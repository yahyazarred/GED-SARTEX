import documents.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("documents", "0024_rename_cabinet_document_index"),
        ("paperless", "0014_builtin_groups"),
    ]

    operations = [
        migrations.CreateModel(
            name="SignatureProfile",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("signature_file", models.FileField(upload_to=documents.models.signature_upload_path)),
                ("original_filename", models.CharField(max_length=255)),
                ("mime_type", models.CharField(max_length=100)),
                ("checksum", models.CharField(editable=False, max_length=64)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="signature_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "signature profile", "verbose_name_plural": "signature profiles"},
        ),
        migrations.CreateModel(
            name="SignatureRequest",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("signed", "Signed"), ("rejected", "Rejected"), ("cancelled", "Cancelled"), ("failed", "Failed")], db_index=True, default="pending", max_length=16)),
                ("message", models.TextField(blank=True, max_length=1000)),
                ("rejection_reason", models.TextField(blank=True, max_length=1000)),
                ("created", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("viewed", models.DateTimeField(blank=True, null=True)),
                ("completed", models.DateTimeField(blank=True, null=True)),
                ("page", models.PositiveIntegerField(blank=True, null=True)),
                ("x", models.FloatField(blank=True, null=True)),
                ("y", models.FloatField(blank=True, null=True)),
                ("width", models.FloatField(blank=True, null=True)),
                ("height", models.FloatField(blank=True, null=True)),
                ("signature_checksum", models.CharField(blank=True, max_length=64)),
                ("failure_message", models.TextField(blank=True)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="signature_requests", to="documents.document")),
                ("requested_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="signature_requests_as_source", to="documents.document")),
                ("requester", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_signature_requests", to=settings.AUTH_USER_MODEL)),
                ("signed_version", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="completed_signature_request", to="documents.document")),
                ("signer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assigned_signature_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("-created",),
            },
        ),
        migrations.AddConstraint(
            model_name="signaturerequest",
            constraint=models.UniqueConstraint(condition=models.Q(("status__in", ["pending", "processing"])), fields=("document", "requested_version", "signer"), name="documents_unique_pending_signature_request"),
        ),
    ]
