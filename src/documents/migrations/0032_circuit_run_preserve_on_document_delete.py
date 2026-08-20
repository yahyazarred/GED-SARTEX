import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documents", "0031_workflow_action_rejection_branches")]

    operations = [
        migrations.AlterField(
            model_name="circuitrun",
            name="document",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="circuit_runs",
                to="documents.document",
            ),
        ),
    ]
