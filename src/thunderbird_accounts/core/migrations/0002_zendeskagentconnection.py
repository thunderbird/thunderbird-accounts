import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import uuid


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_remove_client_tables'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ZendeskAgentConnection',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('zendesk_subdomain', models.CharField(max_length=255)),
                ('zendesk_user_id', models.CharField(max_length=255)),
                ('zendesk_user_email', models.EmailField(blank=True, max_length=254)),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'indexes': [
                    models.Index(fields=['uuid'], name='core_zendes_uuid_725f3e_idx'),
                    models.Index(fields=['created_at'], name='core_zendes_created_fc5531_idx'),
                    models.Index(fields=['updated_at'], name='core_zendes_updated_925cef_idx'),
                    models.Index(fields=['zendesk_subdomain', 'zendesk_user_id'], name='core_zendes_zendesk_306a6a_idx'),
                    models.Index(fields=['zendesk_user_email'], name='core_zendes_zendesk_0984ba_idx'),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='zendeskagentconnection',
            constraint=models.UniqueConstraint(
                fields=('zendesk_subdomain', 'zendesk_user_id'),
                name='unique_zendesk_agent_connection',
            ),
        ),
    ]
