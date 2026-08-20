from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documents", "0030_workflow_action_rejection_route")]

    operations = [
        migrations.AddField(
            model_name="workflowaction",
            name="branch_parent_order",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="workflowaction",
            name="rejection_action_order",
        ),
    ]
