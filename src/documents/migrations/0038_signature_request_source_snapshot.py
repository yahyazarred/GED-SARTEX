import django.db.models.deletion
from django.db import migrations, models


def populate_requested_document_titles(apps, schema_editor):
    signature_request_model = apps.get_model("documents", "SignatureRequest")
    for signature_request in signature_request_model.objects.select_related(
        "requested_version",
    ).iterator():
        if signature_request.requested_version_id:
            signature_request.requested_document_title = (
                signature_request.requested_version.title
            )
            signature_request.save(update_fields=["requested_document_title"])


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0037_remove_redundant_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="signaturerequest",
            name="requested_document_title",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.RunPython(
            populate_requested_document_titles,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="signaturerequest",
            name="requested_version",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="signature_requests_as_source",
                to="documents.document",
            ),
        ),
    ]
