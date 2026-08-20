import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0027_signed_documents"),
    ]

    operations = [
        migrations.AddField(
            model_name="workflow",
            name="is_circuit",
            field=models.BooleanField(default=False, verbose_name="stateful circuit"),
        ),
        migrations.CreateModel(
            name="WorkflowStep",
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
                ("name", models.CharField(max_length=256, verbose_name="name")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="order")),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("action", "Workflow action"),
                            ("approval", "Approval"),
                            ("signature", "Signature request"),
                            ("matching", "Automatic matching"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "approval_mode",
                    models.CharField(
                        choices=[("one", "One member"), ("all", "All members")],
                        default="one",
                        max_length=8,
                    ),
                ),
                (
                    "temporary_access",
                    models.CharField(
                        choices=[
                            ("none", "Do not modify permissions"),
                            ("view", "Grant view access"),
                            ("change", "Grant edit access"),
                        ],
                        default="none",
                        max_length=8,
                    ),
                ),
                (
                    "matching_mode",
                    models.CharField(
                        choices=[
                            ("all", "All matching metadata"),
                            ("tags", "Tags only"),
                            ("cabinet", "Cabinet only"),
                        ],
                        default="all",
                        max_length=16,
                    ),
                ),
                (
                    "action",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="circuit_steps",
                        to="documents.workflowaction",
                    ),
                ),
                (
                    "approval_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approval_steps",
                        to="auth.group",
                    ),
                ),
                (
                    "approval_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approval_steps",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "rejection_step",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="rejection_sources",
                        to="documents.workflowstep",
                    ),
                ),
                (
                    "signature_signer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="signature_steps",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "workflow",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="steps",
                        to="documents.workflow",
                    ),
                ),
            ],
            options={"ordering": ("order", "pk")},
        ),
        migrations.CreateModel(
            name="CircuitRun",
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
                    "trigger_type",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Consumption Started"),
                            (2, "Document Added"),
                            (3, "Document Updated"),
                            (4, "Scheduled"),
                        ],
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("running", "Running"),
                            ("waiting", "Waiting"),
                            ("completed", "Completed"),
                            ("rejected", "Rejected"),
                            ("cancelled", "Cancelled"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="running",
                        max_length=16,
                    ),
                ),
                ("started", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("completed", models.DateTimeField(blank=True, null=True)),
                ("failure_message", models.TextField(blank=True)),
                (
                    "current_step",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="active_runs",
                        to="documents.workflowstep",
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="circuit_runs",
                        to="documents.document",
                    ),
                ),
                (
                    "started_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="started_circuit_runs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "workflow",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="circuit_runs",
                        to="documents.workflow",
                    ),
                ),
            ],
            options={
                "ordering": ("-started",),
                "permissions": [
                    ("monitor_circuitrun", "Can monitor circuit runs"),
                    ("manage_circuitrun", "Can manage circuit runs"),
                ],
            },
        ),
        migrations.CreateModel(
            name="CircuitTask",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("comment", models.TextField(blank=True, max_length=2000)),
                ("created", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("completed", models.DateTimeField(blank=True, null=True)),
                ("attempt", models.PositiveIntegerField(default=1)),
                ("granted_view", models.BooleanField(default=False)),
                ("granted_change", models.BooleanField(default=False)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="circuit_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "decided_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="decided_circuit_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tasks",
                        to="documents.circuitrun",
                    ),
                ),
                (
                    "step",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tasks",
                        to="documents.workflowstep",
                    ),
                ),
            ],
            options={"ordering": ("-created",)},
        ),
        migrations.AddConstraint(
            model_name="workflowstep",
            constraint=models.UniqueConstraint(
                fields=("workflow", "order"),
                name="documents_unique_workflow_step_order",
            ),
        ),
        migrations.AddConstraint(
            model_name="circuitrun",
            constraint=models.UniqueConstraint(
                condition=models.Q(status__in=["running", "waiting"]),
                fields=("workflow", "document"),
                name="documents_unique_active_circuit_run",
            ),
        ),
        migrations.AddConstraint(
            model_name="circuittask",
            constraint=models.UniqueConstraint(
                fields=("run", "step", "assigned_to", "attempt"),
                name="documents_unique_circuit_task_assignee",
            ),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="circuit_run",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="signature_requests",
                to="documents.circuitrun",
            ),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="circuit_step",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="signature_requests",
                to="documents.workflowstep",
            ),
        ),
    ]
