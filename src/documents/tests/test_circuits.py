from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from guardian.shortcuts import assign_perm

from documents.models import CircuitRun
from documents.models import CircuitStepExecution
from documents.models import CircuitTask
from documents.models import Document
from documents.models import SignatureRequest
from documents.models import Workflow
from documents.models import WorkflowAction
from documents.models import WorkflowStep
from documents.workflows.circuits import decide_task
from documents.workflows.circuits import signature_request_completed
from documents.workflows.circuits import start_circuit


class CircuitEngineTest(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user("owner")
        self.approver = User.objects.create_user("approver")
        self.second_approver = User.objects.create_user("second")
        self.signer = User.objects.create_user("signer")
        signers_group = Group.objects.get(built_in_identity__key="signers")
        signers_group.user_set.add(self.signer)
        self.document = Document.objects.create(
            title="Circuit document",
            checksum="1" * 32,
            content="purchase order cabinet finance",
            owner=self.owner,
        )
        assign_perm("view_document", self.signer, self.document)
        self.workflow = Workflow.objects.create(name="Approval circuit", is_circuit=True)

    def test_internal_workflow_models_have_no_global_permissions(self) -> None:
        self.assertEqual(WorkflowStep._meta.default_permissions, ())
        self.assertEqual(CircuitTask._meta.default_permissions, ())
        self.assertEqual(CircuitStepExecution._meta.default_permissions, ())

    def test_single_user_approval_advances_and_cleans_temporary_access(self) -> None:
        WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Manager approval",
            order=0,
            type=WorkflowStep.StepType.APPROVAL,
            approval_user=self.approver,
            temporary_access=WorkflowStep.AccessMode.VIEW,
        )

        run = start_circuit(self.workflow, self.document, actor=self.owner)
        task = run.tasks.get()
        self.assertEqual(run.status, CircuitRun.Status.WAITING)
        self.assertTrue(self.approver.has_perm("documents.view_document", self.document))

        run = decide_task(task, self.approver, True)
        self.approver = User.objects.get(pk=self.approver.pk)
        self.assertEqual(run.status, CircuitRun.Status.COMPLETED)
        self.assertFalse(self.approver.has_perm("documents.view_document", self.document))
        execution = run.step_executions.get()
        self.assertEqual(execution.status, CircuitStepExecution.Status.SUCCEEDED)
        self.assertEqual(execution.actor, self.approver)

    def test_one_member_group_approval_cancels_sibling_tasks(self) -> None:
        group = Group.objects.create(name="Reviewers")
        group.user_set.add(self.approver, self.second_approver)
        WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Review",
            order=0,
            type=WorkflowStep.StepType.APPROVAL,
            approval_group=group,
            approval_mode=WorkflowStep.ApprovalMode.ONE,
        )

        run = start_circuit(self.workflow, self.document)
        task = run.tasks.get(assigned_to=self.approver)
        run = decide_task(task, self.approver, True)

        self.assertEqual(run.status, CircuitRun.Status.COMPLETED)
        self.assertEqual(
            run.tasks.get(assigned_to=self.second_approver).status,
            CircuitTask.Status.CANCELLED,
        )

    def test_all_member_group_approval_waits_for_every_member(self) -> None:
        group = Group.objects.create(name="Board")
        group.user_set.add(self.approver, self.second_approver)
        WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Board approval",
            order=0,
            type=WorkflowStep.StepType.APPROVAL,
            approval_group=group,
            approval_mode=WorkflowStep.ApprovalMode.ALL,
        )

        run = start_circuit(self.workflow, self.document)
        run = decide_task(run.tasks.get(assigned_to=self.approver), self.approver, True)
        self.assertEqual(run.status, CircuitRun.Status.WAITING)
        run = decide_task(
            run.tasks.get(assigned_to=self.second_approver),
            self.second_approver,
            True,
        )
        self.assertEqual(run.status, CircuitRun.Status.COMPLETED)

    def test_only_assignee_can_decide_and_rejection_requires_reason(self) -> None:
        WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Protected approval",
            order=0,
            type=WorkflowStep.StepType.APPROVAL,
            approval_user=self.approver,
        )
        task = start_circuit(self.workflow, self.document).tasks.get()
        with self.assertRaises(PermissionDenied):
            decide_task(task, self.second_approver, True)
        with self.assertRaisesMessage(ValueError, "rejection reason"):
            decide_task(task, self.approver, False)

    def test_rejection_reason_is_recorded_in_step_execution(self) -> None:
        step = WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Approval with audit history",
            order=0,
            type=WorkflowStep.StepType.APPROVAL,
            approval_user=self.approver,
        )
        run = start_circuit(self.workflow, self.document)

        decide_task(run.tasks.get(), self.approver, False, "Invoice total is wrong")

        execution = run.step_executions.get(step=step)
        self.assertEqual(execution.status, CircuitStepExecution.Status.REJECTED)
        self.assertEqual(execution.detail, "Invoice total is wrong")

    def test_rejection_branch_runs_instead_of_stopping(self) -> None:
        branch = WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Rejection handling",
            order=1,
            type=WorkflowStep.StepType.MATCHING,
            matching_mode=WorkflowStep.MatchingMode.TAGS,
        )
        approval = WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Approval",
            order=0,
            type=WorkflowStep.StepType.APPROVAL,
            approval_user=self.approver,
            rejection_step=branch,
        )

        run = start_circuit(self.workflow, self.document)
        run = decide_task(run.tasks.get(step=approval), self.approver, False, "Incorrect")
        self.assertEqual(run.status, CircuitRun.Status.COMPLETED)

    def test_signature_step_waits_and_then_advances(self) -> None:
        step = WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Signature",
            order=0,
            type=WorkflowStep.StepType.SIGNATURE,
            signature_signer=self.signer,
        )

        run = start_circuit(self.workflow, self.document, actor=self.owner)
        request = SignatureRequest.objects.get(circuit_run=run, circuit_step=step)
        self.assertEqual(run.status, CircuitRun.Status.WAITING)
        request.status = SignatureRequest.Status.SIGNED
        request.save(update_fields=["status"])

        run = signature_request_completed(request)
        self.assertEqual(run.status, CircuitRun.Status.COMPLETED)

    def test_rejection_branch_can_move_document_to_trash(self) -> None:
        trash_action = WorkflowAction.objects.create(
            type=WorkflowAction.WorkflowActionType.MOVE_TO_TRASH,
            branch_parent_order=0,
        )
        self.workflow.actions.add(trash_action)
        branch = WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Trash rejected document",
            order=1,
            type=WorkflowStep.StepType.ACTION,
            action=trash_action,
        )
        signature = WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Signature",
            order=0,
            type=WorkflowStep.StepType.SIGNATURE,
            signature_signer=self.signer,
            rejection_step=branch,
        )

        run = start_circuit(self.workflow, self.document, actor=self.owner)
        request = SignatureRequest.objects.get(circuit_run=run, circuit_step=signature)
        request.status = SignatureRequest.Status.REJECTED
        request.save(update_fields=["status"])

        result = signature_request_completed(request)
        persisted = CircuitRun.objects.get(pk=run.pk)
        self.assertEqual(result.status, CircuitRun.Status.COMPLETED)
        self.assertEqual(persisted.status, CircuitRun.Status.COMPLETED)
        self.assertIsNone(persisted.document_id)

    def test_duplicate_active_run_is_rejected(self) -> None:
        WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Approval",
            order=0,
            type=WorkflowStep.StepType.APPROVAL,
            approval_user=self.approver,
        )
        start_circuit(self.workflow, self.document)
        with self.assertRaises(Exception):
            start_circuit(self.workflow, self.document)

    def test_overlapping_temporary_access_is_removed_after_last_task(self) -> None:
        WorkflowStep.objects.create(
            workflow=self.workflow,
            name="First approval",
            order=0,
            type=WorkflowStep.StepType.APPROVAL,
            approval_user=self.approver,
            temporary_access=WorkflowStep.AccessMode.VIEW,
        )
        second_workflow = Workflow.objects.create(
            name="Second approval circuit",
            is_circuit=True,
        )
        WorkflowStep.objects.create(
            workflow=second_workflow,
            name="Second approval",
            order=0,
            type=WorkflowStep.StepType.APPROVAL,
            approval_user=self.approver,
            temporary_access=WorkflowStep.AccessMode.VIEW,
        )
        first = start_circuit(self.workflow, self.document)
        second = start_circuit(second_workflow, self.document)

        decide_task(first.tasks.get(), self.approver, True)
        self.assertTrue(self.approver.has_perm("documents.view_document", self.document))
        decide_task(second.tasks.get(), self.approver, True)
        self.assertFalse(self.approver.has_perm("documents.view_document", self.document))
