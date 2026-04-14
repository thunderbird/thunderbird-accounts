import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LegalDocument',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('document_type', models.CharField(
                    choices=[('tos', 'Terms of Service'), ('privacy', 'Privacy Policy')],
                    max_length=20,
                )),
                ('version', models.CharField(max_length=50)),
                ('is_current', models.BooleanField(default=False)),
                ('content_path', models.CharField(
                    help_text='Relative path to content directory under assets/legal/, e.g. "tos/v1.0"',
                    max_length=255,
                )),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='LegalDocumentResponse',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('action', models.CharField(
                    choices=[('accepted', 'Accepted'), ('declined', 'Declined')],
                    max_length=20,
                )),
                ('source_context', models.CharField(
                    blank=True,
                    default='',
                    help_text='Where the user responded from, e.g. "sign-up", "dashboard", "thundermail"',
                    max_length=255,
                )),
                ('document', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='responses',
                    to='legal.legaldocument',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='legal_responses',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddConstraint(
            model_name='legaldocument',
            constraint=models.UniqueConstraint(
                fields=('document_type', 'version'),
                name='unique_document_type_version',
            ),
        ),
        migrations.AddIndex(
            model_name='legaldocument',
            index=models.Index(fields=['uuid'], name='legal_legald_uuid_idx'),
        ),
        migrations.AddIndex(
            model_name='legaldocument',
            index=models.Index(fields=['created_at'], name='legal_legald_created_idx'),
        ),
        migrations.AddIndex(
            model_name='legaldocument',
            index=models.Index(fields=['updated_at'], name='legal_legald_updated_idx'),
        ),
        migrations.AddIndex(
            model_name='legaldocument',
            index=models.Index(fields=['document_type', 'is_current'], name='legal_legald_doctype_current_idx'),
        ),
        migrations.AddIndex(
            model_name='legaldocumentresponse',
            index=models.Index(fields=['uuid'], name='legal_resp_uuid_idx'),
        ),
        migrations.AddIndex(
            model_name='legaldocumentresponse',
            index=models.Index(fields=['created_at'], name='legal_resp_created_idx'),
        ),
        migrations.AddIndex(
            model_name='legaldocumentresponse',
            index=models.Index(fields=['updated_at'], name='legal_resp_updated_idx'),
        ),
        migrations.AddIndex(
            model_name='legaldocumentresponse',
            index=models.Index(fields=['user', 'document'], name='legal_resp_user_doc_idx'),
        ),
        migrations.AddIndex(
            model_name='legaldocumentresponse',
            index=models.Index(fields=['action'], name='legal_resp_action_idx'),
        ),
    ]
