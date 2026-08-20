from django.db import migrations


def remove_ui_settings_permissions(apps, schema_editor):
    permission_model = apps.get_model("auth", "Permission")
    content_type_model = apps.get_model("contenttypes", "ContentType")
    content_type = content_type_model.objects.filter(
        app_label="documents",
        model="uisettings",
    ).first()
    if content_type is not None:
        permission_model.objects.filter(content_type=content_type).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0035_workflow_activity_permission_names"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="uisettings",
            options={"default_permissions": ()},
        ),
        migrations.RunPython(
            remove_ui_settings_permissions,
            migrations.RunPython.noop,
        ),
    ]
