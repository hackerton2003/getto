import hashlib

from django.db import migrations, models


def hash_existing_reset_tokens(apps, schema_editor):
    PasswordReset = apps.get_model("authentication", "PasswordReset")
    database = schema_editor.connection.alias
    for reset in PasswordReset.objects.using(database).all().iterator():
        reset.token_hash = hashlib.sha256(reset.token_hash.encode("utf-8")).hexdigest()
        reset.save(using=database, update_fields=("token_hash",))


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0002_authsession"),
    ]

    operations = [
        migrations.RenameField(
            model_name="passwordreset",
            old_name="token",
            new_name="token_hash",
        ),
        migrations.RunPython(
            hash_existing_reset_tokens,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="passwordreset",
            name="token_hash",
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
