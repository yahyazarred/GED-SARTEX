from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max
from django.db.models import Q
from django.utils import timezone
from guardian.shortcuts import assign_perm
from guardian.shortcuts import remove_perm

from documents.models import CircuitRun
from documents.models import CircuitStepExecution
from documents.models import CircuitTask
from documents.models import Document
from documents.models import SignatureRequest
from documents.models import SignedDocument
from documents.models import Workflow
from documents.models import WorkflowAction
from documents.models import WorkflowStep
from documents.models import WorkflowTrigger
from documents.workflows.actions import build_workflow_action_context
from documents.workflows.actions import execute_email_action
from documents.workflows.actions import execute_move_to_trash_action
from documents.workflows.actions import execute_password_removal_action
from documents.workflows.actions import execute_webhook_action
from documents.workflows.mutations import apply_assignment_to_document
from documents.workflows.mutations import apply_removal_to_document

logger = logging.getLogger("paperless.workflows.circuits")


def _start_step_execution(run: CircuitRun, step: WorkflowStep) -> CircuitStepExecution:
    active = (
        run.step_executions.filter(
            step=step,
            status__in=[
                CircuitStepExecution.Status.RUNNING,
                CircuitStepExecution.Status.WAITING,
            ],
        )
        .order_by("-attempt")
        .first()
    )
    if active:
        return active
    attempt = (
        run.step_executions.filter(step=step).aggregate(maximum=Max("attempt"))["maximum"]
        or 0
    ) + 1
    return CircuitStepExecution.objects.create(
        run=run,
        step=step,
        attempt=attempt,
        status=CircuitStepExecution.Status.RUNNING,
    )


def _finish_step_execution(
    run: CircuitRun,
    step: WorkflowStep,
    status: CircuitStepExecution.Status,
    *,
    actor: User | None = None,
    detail: str = "",
    error: str = "",
) -> CircuitStepExecution:
    execution = _start_step_execution(run, step)
    execution.status = status
    execution.actor = actor
    execution.detail = detail[:2000]
    execution.error = error[:4000]
    execution.completed = timezone.now()
    execution.save(
        update_fields=["status", "actor", "detail", "error", "completed"],
    )
    return execution


def notify_circuit_task(task: CircuitTask) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            "status_updates",
            {
                "type": "circuit_task_updated",
                "data": {
                    "task_id": task.pk,
                    "run_id": task.run_id,
                    "document_id": task.run.document_id,
                    "status": task.status,
                    "users_can_view": [task.assigned_to_id],
                    "groups_can_view": [],
                },
            },
        )
    except Exception:
        logger.warning("Unable to send circuit task update", exc_info=True)


def _prepare_action(action: WorkflowAction) -> WorkflowAction:
    for relation in (
        "assign_tags",
        "assign_view_users",
        "assign_view_groups",
        "assign_change_users",
        "assign_change_groups",
        "assign_custom_fields",
        "remove_view_users",
        "remove_view_groups",
        "remove_change_users",
        "remove_change_groups",
        "remove_custom_fields",
    ):
        setattr(action, f"has_{relation}", getattr(action, relation).exists())
    return action


def _execute_action(action: WorkflowAction, document: Document, trigger_type) -> None:
    action = _prepare_action(action)
    move_to_trash = False
    if action.type == WorkflowAction.WorkflowActionType.ASSIGNMENT:
        apply_assignment_to_document(action, document, None)
    elif action.type == WorkflowAction.WorkflowActionType.REMOVAL:
        apply_removal_to_document(action, document)
    elif action.type == WorkflowAction.WorkflowActionType.EMAIL:
        execute_email_action(
            action,
            document,
            build_workflow_action_context(document, None),
            None,
            document.source_path,
            trigger_type,
        )
    elif action.type == WorkflowAction.WorkflowActionType.WEBHOOK:
        execute_webhook_action(
            action,
            document,
            build_workflow_action_context(document, None),
            None,
            document.source_path,
        )
    elif action.type == WorkflowAction.WorkflowActionType.PASSWORD_REMOVAL:
        execute_password_removal_action(action, document, None)
    elif action.type == WorkflowAction.WorkflowActionType.MOVE_TO_TRASH:
        move_to_trash = True
    document.title = document.title[:128]
    document.save(
        update_fields=[
            "title",
            "correspondent",
            "document_type",
            "storage_path",
            "cabinet",
            "inherit_cabinet_permissions",
            "owner",
            "modified",
        ],
    )
    if move_to_trash:
        execute_move_to_trash_action(action, document, None)


def _run_matching(step: WorkflowStep, document: Document) -> None:
    # Import lazily: handlers owns the established automatic-matching functions and
    # also imports the circuit entry point from its workflow runner.
    from documents.classifier import load_classifier
    from documents.signals.handlers import set_cabinet
    from documents.signals.handlers import set_correspondent
    from documents.signals.handlers import set_document_type
    from documents.signals.handlers import set_storage_path
    from documents.signals.handlers import set_tags

    classifier = load_classifier()

    if step.matching_mode in (WorkflowStep.MatchingMode.ALL, WorkflowStep.MatchingMode.TAGS):
        set_tags(None, document, classifier=classifier)
    if step.matching_mode in (WorkflowStep.MatchingMode.ALL, WorkflowStep.MatchingMode.CABINET):
        set_cabinet(None, document, classifier=classifier)
    if step.matching_mode == WorkflowStep.MatchingMode.ALL:
        set_correspondent(None, document, classifier=classifier)
        set_document_type(None, document, classifier=classifier)
        set_storage_path(None, document, classifier=classifier)


def _grant_task_access(task: CircuitTask) -> None:
    document = task.run.document
    user = task.assigned_to
    mode = task.step.temporary_access
    if mode in (WorkflowStep.AccessMode.VIEW, WorkflowStep.AccessMode.CHANGE):
        if not user.has_perm("documents.view_document", document):
            assign_perm("view_document", user, document)
            task.granted_view = True
        elif CircuitTask.objects.filter(
            run__document=document,
            assigned_to=user,
            status=CircuitTask.Status.PENDING,
            granted_view=True,
        ).exclude(pk=task.pk).exists():
            task.granted_view = True
    if mode == WorkflowStep.AccessMode.CHANGE:
        if not user.has_perm("documents.change_document", document):
            assign_perm("change_document", user, document)
            task.granted_change = True
        elif CircuitTask.objects.filter(
            run__document=document,
            assigned_to=user,
            status=CircuitTask.Status.PENDING,
            granted_change=True,
        ).exclude(pk=task.pk).exists():
            task.granted_change = True
    task.save(update_fields=["granted_view", "granted_change"])


def _revoke_task_access(task: CircuitTask) -> None:
    other_tasks = CircuitTask.objects.filter(
        run__document=task.run.document,
        assigned_to=task.assigned_to,
        status=CircuitTask.Status.PENDING,
    ).exclude(pk=task.pk)
    if task.granted_change and not other_tasks.filter(granted_change=True).exists():
        remove_perm("change_document", task.assigned_to, task.run.document)
    if task.granted_view and not other_tasks.filter(granted_view=True).exists():
        remove_perm("view_document", task.assigned_to, task.run.document)


def _next_step(step: WorkflowStep) -> WorkflowStep | None:
    if step.action_id is None:
        return (
            step.workflow.steps.filter(order__gt=step.order)
            .order_by("order", "pk")
            .first()
        )
    branch_parent_order = step.action.branch_parent_order
    branch_filter = (
        {"action__branch_parent_order": branch_parent_order}
        if branch_parent_order is not None
        else {"action__branch_parent_order__isnull": True}
    )
    return (
        step.workflow.steps.filter(
            order__gt=step.order,
            action__workflows=step.workflow,
            **branch_filter,
        )
        .order_by("order", "pk")
        .first()
    )


def start_circuit(
    workflow: Workflow,
    document: Document,
    trigger_type: WorkflowTrigger.WorkflowTriggerType | None = None,
    actor: User | None = None,
) -> CircuitRun:
    if not workflow.is_circuit:
        raise ValueError("Only stateful workflows can be started as circuits.")
    document = document.root_document or document
    first_step = (
        workflow.steps.filter(
            Q(action__isnull=True)
            | Q(
                action__workflows=workflow,
                action__branch_parent_order__isnull=True,
            ),
        )
        .order_by("order", "pk")
        .first()
    )
    with transaction.atomic():
        run = CircuitRun.objects.create(
            workflow=workflow,
            document=document,
            trigger_type=trigger_type,
            current_step=first_step,
            started_by=actor,
        )
    return advance_circuit(run.pk)


def advance_circuit(run_id: int) -> CircuitRun:
    with transaction.atomic():
        run = CircuitRun.objects.select_for_update().select_related(
            "document",
            "workflow",
            "current_step",
        ).get(pk=run_id)
        if run.status in (
            CircuitRun.Status.COMPLETED,
            CircuitRun.Status.REJECTED,
            CircuitRun.Status.CANCELLED,
            CircuitRun.Status.FAILED,
        ):
            return run

        while run.current_step_id:
            step = run.current_step
            execution = _start_step_execution(run, step)
            try:
                if step.type == WorkflowStep.StepType.ACTION:
                    if (
                        step.action.type
                        == WorkflowAction.WorkflowActionType.MOVE_TO_TRASH
                    ):
                        run.current_step = None
                        run.status = CircuitRun.Status.COMPLETED
                        run.completed = timezone.now()
                        run.save(
                            update_fields=[
                                "current_step",
                                "status",
                                "completed",
                                "modified",
                            ],
                        )
                        _execute_action(
                            step.action,
                            run.document,
                            run.trigger_type,
                        )
                        _finish_step_execution(
                            run,
                            step,
                            CircuitStepExecution.Status.SUCCEEDED,
                        )
                        return run
                    _execute_action(step.action, run.document, run.trigger_type)
                elif step.type == WorkflowStep.StepType.MATCHING:
                    _run_matching(step, run.document)
                elif step.type == WorkflowStep.StepType.APPROVAL:
                    if CircuitTask.objects.filter(
                        run=run,
                        step=step,
                        status=CircuitTask.Status.PENDING,
                    ).exists():
                        execution.status = CircuitStepExecution.Status.WAITING
                        execution.save(update_fields=["status"])
                        run.status = CircuitRun.Status.WAITING
                        run.save(update_fields=["status", "modified"])
                        return run
                    users = (
                        [step.approval_user]
                        if step.approval_user_id
                        else list(step.approval_group.user_set.filter(is_active=True))
                    )
                    if not users:
                        raise ValueError("The approval step has no active approvers.")
                    attempt = (
                        CircuitTask.objects.filter(run=run, step=step).aggregate(
                            maximum=Max("attempt"),
                        )["maximum"]
                        or 0
                    ) + 1
                    for user in users:
                        task = CircuitTask.objects.create(
                            run=run,
                            step=step,
                            assigned_to=user,
                            attempt=attempt,
                        )
                        _grant_task_access(task)
                        notify_circuit_task(task)
                    execution.status = CircuitStepExecution.Status.WAITING
                    execution.save(update_fields=["status"])
                    run.status = CircuitRun.Status.WAITING
                    run.save(update_fields=["status", "modified"])
                    return run
                elif step.type == WorkflowStep.StepType.SIGNATURE:
                    signer = step.signature_signer
                    if not signer.groups.filter(
                        built_in_identity__key="signers",
                    ).exists():
                        raise ValueError("The configured user is not an active signer.")
                    if not signer.has_perm("documents.view_document", run.document):
                        raise PermissionDenied(
                            "The configured signer cannot view this document.",
                        )
                    requester = run.started_by or run.document.owner
                    if requester is None:
                        requester = User.objects.filter(is_superuser=True, is_active=True).first()
                    if requester is None:
                        raise ValueError("No user is available to own the signature request.")
                    requested_version = run.document.versions.order_by(
                        "-version_index",
                        "-pk",
                    ).first()
                    requested_version = requested_version or run.document
                    if SignedDocument.objects.filter(
                        source_version=requested_version,
                        signer=signer,
                    ).exists():
                        raise ValueError(
                            "The configured signer has already signed this document version.",
                        )
                    signature_request = SignatureRequest.objects.create(
                        document=run.document,
                        requested_version=requested_version,
                        requester=requester,
                        signer=signer,
                        circuit_run=run,
                        circuit_step=step,
                        message=f"Requested automatically by circuit {run.workflow.name}",
                    )
                    from documents.views import _log_signature_event
                    from documents.views import _notify_signature_request

                    _notify_signature_request(signature_request)
                    _log_signature_event(
                        signature_request,
                        "Signature Requested by Circuit",
                        requester,
                    )
                    execution.status = CircuitStepExecution.Status.WAITING
                    execution.save(update_fields=["status"])
                    run.status = CircuitRun.Status.WAITING
                    run.save(update_fields=["status", "modified"])
                    return run
            except Exception as exc:
                logger.exception("Circuit %s failed at step %s", run.pk, step.pk)
                _finish_step_execution(
                    run,
                    step,
                    CircuitStepExecution.Status.FAILED,
                    error=str(exc),
                )
                run.status = CircuitRun.Status.FAILED
                run.failure_message = str(exc)
                run.completed = timezone.now()
                run.save(
                    update_fields=["status", "failure_message", "completed", "modified"],
                )
                return run

            _finish_step_execution(
                run,
                step,
                CircuitStepExecution.Status.SUCCEEDED,
            )
            run.current_step = _next_step(step)
            run.save(update_fields=["current_step", "modified"])

        run.status = CircuitRun.Status.COMPLETED
        run.completed = timezone.now()
        run.save(update_fields=["status", "completed", "modified"])
        return run


def decide_task(task: CircuitTask, user: User, approved: bool, comment: str = "") -> CircuitRun:
    if task.assigned_to_id != user.pk:
        raise PermissionDenied("This approval task is assigned to another user.")
    if task.status != CircuitTask.Status.PENDING:
        raise ValueError("Only pending approval tasks can be decided.")
    if not approved and not comment.strip():
        raise ValueError("A rejection reason is required.")

    with transaction.atomic():
        task = CircuitTask.objects.select_for_update().select_related(
            "run",
            "step",
            "run__document",
        ).get(pk=task.pk)
        task.status = CircuitTask.Status.APPROVED if approved else CircuitTask.Status.REJECTED
        task.comment = comment.strip()
        task.decided_by = user
        task.completed = timezone.now()
        task.save(update_fields=["status", "comment", "decided_by", "completed"])
        _revoke_task_access(task)
        notify_circuit_task(task)

        run = CircuitRun.objects.select_for_update().get(pk=task.run_id)
        siblings = CircuitTask.objects.filter(
            run=run,
            step=task.step,
            attempt=task.attempt,
        )
        if not approved:
            _finish_step_execution(
                run,
                task.step,
                CircuitStepExecution.Status.REJECTED,
                actor=user,
                detail=task.comment,
            )
            for sibling in siblings.filter(status=CircuitTask.Status.PENDING):
                sibling.status = CircuitTask.Status.CANCELLED
                sibling.completed = timezone.now()
                sibling.save(update_fields=["status", "completed"])
                _revoke_task_access(sibling)
                notify_circuit_task(sibling)
            if task.step.rejection_step_id:
                run.current_step = task.step.rejection_step
                run.status = CircuitRun.Status.RUNNING
                run.save(update_fields=["current_step", "status", "modified"])
                return advance_circuit(run.pk)
            run.status = CircuitRun.Status.REJECTED
            run.completed = timezone.now()
            run.save(update_fields=["status", "completed", "modified"])
            return run

        complete = (
            task.step.approval_mode == WorkflowStep.ApprovalMode.ONE
            or not siblings.filter(status=CircuitTask.Status.PENDING).exists()
        )
        if complete:
            if task.step.approval_mode == WorkflowStep.ApprovalMode.ONE:
                for sibling in siblings.filter(status=CircuitTask.Status.PENDING):
                    sibling.status = CircuitTask.Status.CANCELLED
                    sibling.completed = timezone.now()
                    sibling.save(update_fields=["status", "completed"])
                    _revoke_task_access(sibling)
                    notify_circuit_task(sibling)
            _finish_step_execution(
                run,
                task.step,
                CircuitStepExecution.Status.SUCCEEDED,
                actor=user,
                detail=task.comment,
            )
            run.current_step = _next_step(task.step)
            run.status = CircuitRun.Status.RUNNING
            run.save(update_fields=["current_step", "status", "modified"])
            return advance_circuit(run.pk)
        return run


def signature_request_completed(request: SignatureRequest) -> CircuitRun | None:
    if not request.circuit_run_id or request.circuit_run.status != CircuitRun.Status.WAITING:
        return None
    run = request.circuit_run
    if request.status == SignatureRequest.Status.SIGNED:
        _finish_step_execution(
            run,
            request.circuit_step,
            CircuitStepExecution.Status.SUCCEEDED,
            actor=request.signer,
            detail="Signature completed.",
        )
        run.current_step = _next_step(request.circuit_step)
        run.status = CircuitRun.Status.RUNNING
        run.save(update_fields=["current_step", "status", "modified"])
        return advance_circuit(run.pk)
    if request.status in (
        SignatureRequest.Status.REJECTED,
        SignatureRequest.Status.CANCELLED,
        SignatureRequest.Status.FAILED,
    ):
        detail = request.rejection_reason or request.failure_message
        execution_status = {
            SignatureRequest.Status.REJECTED: CircuitStepExecution.Status.REJECTED,
            SignatureRequest.Status.CANCELLED: CircuitStepExecution.Status.CANCELLED,
            SignatureRequest.Status.FAILED: CircuitStepExecution.Status.FAILED,
        }[request.status]
        _finish_step_execution(
            run,
            request.circuit_step,
            execution_status,
            actor=request.signer,
            detail=detail,
            error=request.failure_message,
        )
        if request.circuit_step.rejection_step_id:
            run.current_step = request.circuit_step.rejection_step
            run.status = CircuitRun.Status.RUNNING
            run.save(update_fields=["current_step", "status", "modified"])
            return advance_circuit(run.pk)
        run.status = CircuitRun.Status.REJECTED
        run.completed = timezone.now()
        run.save(update_fields=["status", "completed", "modified"])
    return run
