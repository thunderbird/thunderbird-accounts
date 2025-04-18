# Generated by Django 5.1.3 on 2024-11-28 22:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0006_alter_clientenvironment_auth_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='clientenvironment',
            name='allowed_hostnames',
            field=models.JSONField(default=list, help_text='List of allowed hostnames for this client environment.'),
        ),
    ]
