from django.db import migrations, models


def copy_rejection_routes(apps, schema_editor):
    Workflow = apps.get_model("documents", "Workflow")
    for workflow in Workflow.objects.filter(is_circuit=True).iterator():
        steps = list(workflow.steps.order_by("order", "pk"))
        step_orders = {step.pk: index for index, step in enumerate(steps)}
        for index, step in enumerate(steps):
            if step.action_id and step.rejection_step_id:
                target_order = step_orders.get(step.rejection_step_id)
                if target_order is not None and target_order > index:
                    step.action.rejection_action_order = target_order
                    step.action.save(update_fields=["rejection_action_order"])


class Migration(migrations.Migration):
    dependencies = [("documents", "0029_workflow_actions_as_steps")]

    operations = [
        migrations.AddField(
            model_name="workflowaction",
            name="rejection_action_order",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(copy_rejection_routes, migrations.RunPython.noop),
    ]
