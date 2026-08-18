from django.db import migrations, models
import django.db.models.deletion


def create_signers_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    BuiltInGroup = apps.get_model("paperless", "BuiltInGroup")
    group, _ = Group.objects.get_or_create(name="Signers")
    BuiltInGroup.objects.get_or_create(key="signers", defaults={"group": group})


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("paperless", "0013_applicationconfiguration_llm_request_timeout"),
    ]

    operations = [
        migrations.CreateModel(
            name="BuiltInGroup",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(choices=[("signers", "Signers")], max_length=64, unique=True)),
                ("group", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="built_in_identity", to="auth.group")),
            ],
            options={"verbose_name": "built-in group", "verbose_name_plural": "built-in groups"},
        ),
        migrations.RunPython(create_signers_group, migrations.RunPython.noop),
    ]
