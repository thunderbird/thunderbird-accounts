# Generated by Django 5.1.7 on 2025-04-03 18:18

from django.db import migrations

from thunderbird_accounts.client.models import _generate_secret


def gen_secrets(apps, schema_editor):
    webhook = apps.get_model('client', 'ClientWebhook')
    for row in webhook.objects.all():
        row.secret = _generate_secret()
        row.save(update_fields=['secret'])


class Migration(migrations.Migration):
    dependencies = [
        ('client', '0011_clientwebhook_secret'),
    ]

    operations = [
        # omit reverse_code=... if you don't want the migration to be reversible.
        migrations.RunPython(gen_secrets, reverse_code=migrations.RunPython.noop),
    ]
