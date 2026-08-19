import hashlib
from pathlib import Path

import django.db.models.deletion
import documents.models
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import migrations
from django.db import models
import django.utils.timezone


def migrate_signed_versions(apps, schema_editor):
    SignatureRequest = apps.get_model("documents", "SignatureRequest")
    SignedDocument = apps.get_model("documents", "SignedDocument")
    requests = SignatureRequest.objects.exclude(signed_version_id=None).order_by(
        "-completed",
        "-created",
    )
    for request in requests.iterator():
        version = request.signed_version
        if SignedDocument.objects.filter(
            source_version_id=request.requested_version_id,
            signer_id=request.signer_id,
        ).exists():
            request.status = "failed"
            request.failure_message = (
                "A newer signed copy for this signer and version was migrated."
            )
            request.save(update_fields=["status", "failure_message"])
            continue
        if version.archive_filename:
            source_path = Path(settings.ARCHIVE_DIR) / Path(str(version.archive_filename))
        else:
            filename = (
                str(version.filename)
                if version.filename
                else f"{version.pk:07}{version.file_type}"
            )
            source_path = Path(settings.ORIGINALS_DIR) / Path(filename)
        if not source_path.is_file():
            request.status = "failed"
            request.failure_message = "Legacy signed version file could not be migrated."
            request.save(update_fields=["status", "failure_message"])
            continue
        data = source_path.read_bytes()
        signed_document = SignedDocument(
            signature_request=request,
            document_id=request.document_id,
            source_version_id=request.requested_version_id,
            signer_id=request.signer_id,
            requester_id=request.requester_id,
            owner_id=request.requester_id,
            file_checksum=hashlib.sha256(data).hexdigest(),
            signature_checksum=request.signature_checksum,
            created=request.completed or request.created,
            page=request.page or 1,
            x=request.x or 0,
            y=request.y or 0,
            width=request.width or 0.2,
            height=request.height or 0.1,
        )
        signed_document.signed_file.save(
            "signed.pdf",
            ContentFile(data),
            save=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0026_signatureprofile_processed_file"),
    ]

    operations = [
        migrations.CreateModel(
            name="SignedDocument",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "signed_file",
                    models.FileField(
                        upload_to=documents.models.signed_document_upload_path,
                    ),
                ),
                ("file_checksum", models.CharField(editable=False, max_length=64)),
                (
                    "signature_checksum",
                    models.CharField(editable=False, max_length=64),
                ),
                (
                    "created",
                    models.DateTimeField(
                        db_index=True,
                        default=django.utils.timezone.now,
                    ),
                ),
                ("page", models.PositiveIntegerField()),
                ("x", models.FloatField()),
                ("y", models.FloatField()),
                ("width", models.FloatField()),
                ("height", models.FloatField()),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="signed_documents",
                        to="documents.document",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="owner",
                    ),
                ),
                (
                    "requester",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="requested_signed_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "signature_request",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="signed_document",
                        to="documents.signaturerequest",
                    ),
                ),
                (
                    "signer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="signed_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source_version",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="signed_copies_as_source",
                        to="documents.document",
                    ),
                ),
            ],
            options={"ordering": ("-created",)},
        ),
        migrations.AddConstraint(
            model_name="signeddocument",
            constraint=models.UniqueConstraint(
                fields=("source_version", "signer"),
                name="documents_unique_signed_copy_per_version_signer",
            ),
        ),
        migrations.RunPython(migrate_signed_versions, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="signaturerequest",
            name="signed_version",
        ),
    ]
