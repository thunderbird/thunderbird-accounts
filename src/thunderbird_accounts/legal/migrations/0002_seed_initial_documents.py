from django.db import migrations


def seed_legal_documents(apps, schema_editor):
    LegalDocument = apps.get_model('legal', 'LegalDocument')

    LegalDocument.objects.get_or_create(
        document_type='tos',
        version='1.0',
        defaults={
            'is_current': True,
            'content_path': 'tos/v1.0',
        },
    )
    LegalDocument.objects.get_or_create(
        document_type='privacy',
        version='1.0',
        defaults={
            'is_current': True,
            'content_path': 'privacy/v1.0',
        },
    )


def unseed_legal_documents(apps, schema_editor):
    LegalDocument = apps.get_model('legal', 'LegalDocument')
    LegalDocument.objects.filter(
        document_type__in=['tos', 'privacy'],
        version='1.0',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('legal', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_legal_documents, unseed_legal_documents),
    ]
