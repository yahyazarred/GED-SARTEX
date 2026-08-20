from django.db import migrations


def remove_builtin_group_permissions(apps, schema_editor):
    permission_model = apps.get_model("auth", "Permission")
    content_type_model = apps.get_model("contenttypes", "ContentType")
    content_type = content_type_model.objects.filter(
        app_label="paperless",
        model="builtingroup",
    ).first()
    if content_type is not None:
        permission_model.objects.filter(content_type=content_type).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("paperless", "0014_builtin_groups"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="builtingroup",
            options={
                "default_permissions": (),
                "verbose_name": "built-in group",
                "verbose_name_plural": "built-in groups",
            },
        ),
        migrations.RunPython(
            remove_builtin_group_permissions,
            migrations.RunPython.noop,
        ),
    ]
