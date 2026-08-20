import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def unify_existing_workflow_steps(apps, schema_editor):
    Workflow = apps.get_model("documents", "Workflow")
    WorkflowAction = apps.get_model("documents", "WorkflowAction")

    type_map = {"approval": 7, "signature": 8, "matching": 9}
    for workflow in Workflow.objects.filter(is_circuit=True).iterator():
        ordered_actions = []
        for order, step in enumerate(workflow.steps.order_by("order", "pk")):
            action = step.action
            if action is None and step.type in type_map:
                action = WorkflowAction.objects.create(
                    type=type_map[step.type],
                    order=order,
                    approval_user=step.approval_user,
                    approval_group=step.approval_group,
                    approval_mode=step.approval_mode,
                    temporary_access=step.temporary_access,
                    signature_signer=step.signature_signer,
                    matching_mode=step.matching_mode,
                )
                step.action = action
                step.save(update_fields=["action"])
            if action is not None:
                action.order = order
                action.save(update_fields=["order"])
                ordered_actions.append(action)
        workflow.actions.set(ordered_actions)


class Migration(migrations.Migration):
    dependencies = [("documents", "0028_workflow_circuits")]

    operations = [
        migrations.AlterField(
            model_name="workflowaction",
            name="type",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "Assignment"),
                    (2, "Removal"),
                    (3, "Email"),
                    (4, "Webhook"),
                    (5, "Password removal"),
                    (6, "Move to trash"),
                    (7, "Approval"),
                    (8, "Request signature"),
                    (9, "Automatic matching"),
                ],
                default=1,
                verbose_name="Workflow Action Type",
            ),
        ),
        migrations.AddField(
            model_name="workflowaction",
            name="approval_group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="workflow_approval_actions",
                to="auth.group",
            ),
        ),
        migrations.AddField(
            model_name="workflowaction",
            name="approval_mode",
            field=models.CharField(
                choices=[("one", "One member"), ("all", "All members")],
                default="one",
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name="workflowaction",
            name="approval_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="workflow_approval_actions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="workflowaction",
            name="matching_mode",
            field=models.CharField(
                choices=[
                    ("all", "All matching metadata"),
                    ("tags", "Tags only"),
                    ("cabinet", "Cabinet only"),
                ],
                default="all",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="workflowaction",
            name="signature_signer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="workflow_signature_actions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="workflowaction",
            name="temporary_access",
            field=models.CharField(
                choices=[
                    ("none", "Do not modify permissions"),
                    ("view", "Grant view access"),
                    ("change", "Grant edit access"),
                ],
                default="none",
                max_length=8,
            ),
        ),
        migrations.RunPython(
            unify_existing_workflow_steps,
            migrations.RunPython.noop,
        ),
    ]
