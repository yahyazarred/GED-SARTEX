from django.db import migrations


def migrate_workflow_activity_permissions(apps, schema_editor):
    permission_model = apps.get_model("auth", "Permission")
    content_type_model = apps.get_model("contenttypes", "ContentType")
    content_type = content_type_model.objects.filter(
        app_label="documents",
        model="circuitrun",
    ).first()
    # Content types are created by post_migrate. They are therefore absent while
    # a completely new database (including pytest's test database) is still
    # applying its initial migrations. Existing installations already have this
    # row and still receive the permission-assignment migration below.
    if content_type is None:
        return
    for old_codename, new_codename in (
        ("monitor_circuitrun", "view_circuitrun"),
        ("manage_circuitrun", "change_circuitrun"),
    ):
        old_permission = permission_model.objects.filter(
            content_type=content_type,
            codename=old_codename,
        ).first()
        new_permission = permission_model.objects.filter(
            content_type=content_type,
            codename=new_codename,
        ).first()
        if old_permission is None or new_permission is None:
            continue
        new_permission.user_set.add(*old_permission.user_set.all())
        new_permission.group_set.add(*old_permission.group_set.all())


def remove_redundant_permissions(apps, schema_editor):
    permission_model = apps.get_model("auth", "Permission")
    content_type_model = apps.get_model("contenttypes", "ContentType")
    removals = {
        "circuittask": {"add", "change", "delete", "view"},
        "circuitstepexecution": {"add", "change", "delete", "view"},
        "workflowstep": {"add", "change", "delete", "view"},
        "signatureprofile": {"add", "change", "delete", "view"},
        "signeddocument": {"add"},
        "signaturerequest": {"delete"},
        "circuitrun": {"delete", "monitor", "manage"},
    }
    for model, actions in removals.items():
        content_type = content_type_model.objects.filter(
            app_label="documents",
            model=model,
        ).first()
        if content_type is None:
            continue
        codenames = [f"{action}_{model}" for action in actions]
        permission_model.objects.filter(
            content_type=content_type,
            codename__in=codenames,
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0036_remove_ui_settings_permissions"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="signatureprofile",
            options={
                "default_permissions": (),
                "verbose_name": "signature profile",
                "verbose_name_plural": "signature profiles",
            },
        ),
        migrations.AlterModelOptions(
            name="signeddocument",
            options={
                "default_permissions": ("change", "delete", "view"),
                "ordering": ("-created",),
            },
        ),
        migrations.AlterModelOptions(
            name="signaturerequest",
            options={
                "default_permissions": ("add", "change", "view"),
                "ordering": ("-created",),
            },
        ),
        migrations.AlterModelOptions(
            name="workflowstep",
            options={"default_permissions": (), "ordering": ("order", "pk")},
        ),
        migrations.AlterModelOptions(
            name="circuitrun",
            options={
                "default_permissions": ("add", "change", "view"),
                "ordering": ("-started",),
                "verbose_name": "workflow activity",
                "verbose_name_plural": "workflow activity",
            },
        ),
        migrations.AlterModelOptions(
            name="circuitstepexecution",
            options={"default_permissions": (), "ordering": ("started", "pk")},
        ),
        migrations.AlterModelOptions(
            name="circuittask",
            options={"default_permissions": (), "ordering": ("-created",)},
        ),
        migrations.RunPython(
            migrate_workflow_activity_permissions,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            remove_redundant_permissions,
            migrations.RunPython.noop,
        ),
    ]
