import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0032_circuit_run_preserve_on_document_delete"),
    ]

    operations = [
        migrations.AlterField(
            model_name="signaturerequest",
            name="document",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="signature_requests",
                to="documents.document",
            ),
        ),
    ]
