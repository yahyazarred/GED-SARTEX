import documents.models
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0025_signatures"),
    ]

    operations = [
        migrations.AddField(
            model_name="signatureprofile",
            name="processed_file",
            field=models.FileField(
                blank=True,
                upload_to=documents.models.processed_signature_upload_path,
            ),
        ),
    ]
