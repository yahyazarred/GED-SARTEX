from django.db import migrations, models


def rename_permissions(apps, schema_editor):
    permission_model = apps.get_model("auth", "Permission")
    content_type_model = apps.get_model("contenttypes", "ContentType")
    content_type = content_type_model.objects.filter(
        app_label="documents",
        model="circuitrun",
    ).first()
    if content_type is None:
        return
    permission_model.objects.filter(
        content_type=content_type,
        codename="monitor_circuitrun",
    ).update(name="Can monitor workflow activity")
    permission_model.objects.filter(
        content_type=content_type,
        codename="manage_circuitrun",
    ).update(name="Can manage workflow activity")
    for action in ("add", "change", "delete", "view"):
        permission_model.objects.filter(
            content_type=content_type,
            codename=f"{action}_circuitrun",
        ).update(name=f"Can {action} workflow activity")


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0034_circuit_step_execution"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workflow",
            name="is_circuit",
            field=models.BooleanField(default=False, verbose_name="stateful workflow"),
        ),
        migrations.AlterModelOptions(
            name="circuitrun",
            options={
                "ordering": ("-started",),
                "permissions": [
                    ("monitor_circuitrun", "Can monitor workflow activity"),
                    ("manage_circuitrun", "Can manage workflow activity"),
                ],
                "verbose_name": "workflow activity",
                "verbose_name_plural": "workflow activity",
            },
        ),
        migrations.RunPython(rename_permissions, migrations.RunPython.noop),
    ]
