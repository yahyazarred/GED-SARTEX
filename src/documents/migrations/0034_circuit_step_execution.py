import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0033_preserve_signature_requests_in_trash"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CircuitStepExecution",
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
                ("attempt", models.PositiveIntegerField(default=1)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("running", "Running"),
                            ("waiting", "Waiting"),
                            ("succeeded", "Succeeded"),
                            ("rejected", "Rejected"),
                            ("failed", "Failed"),
                            ("skipped", "Skipped"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        max_length=16,
                    ),
                ),
                (
                    "started",
                    models.DateTimeField(
                        db_index=True,
                        default=django.utils.timezone.now,
                    ),
                ),
                ("completed", models.DateTimeField(blank=True, null=True)),
                ("detail", models.TextField(blank=True, max_length=2000)),
                ("error", models.TextField(blank=True, max_length=4000)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="circuit_step_executions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="step_executions",
                        to="documents.circuitrun",
                    ),
                ),
                (
                    "step",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="executions",
                        to="documents.workflowstep",
                    ),
                ),
            ],
            options={"ordering": ("started", "pk")},
        ),
        migrations.AddConstraint(
            model_name="circuitstepexecution",
            constraint=models.UniqueConstraint(
                fields=("run", "step", "attempt"),
                name="documents_unique_circuit_step_attempt",
            ),
        ),
    ]
