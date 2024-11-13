# Generated by Django 5.1.3 on 2024-11-12 21:10

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
            name='Customer',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('paddle_id', models.CharField(max_length=256)),
                ('name', models.CharField(max_length=128)),
                ('email', models.CharField(max_length=256)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=128)),
                ('paddle_id', models.CharField(max_length=256)),
                ('is_active', models.BooleanField()),
                ('active_since', models.DateTimeField()),
                ('inactive_since', models.DateTimeField()),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='subscription.customer')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['uuid'], name='subscriptio_uuid_9a398f_idx'),
        ),
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['created_at'], name='subscriptio_created_e9a881_idx'),
        ),
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['updated_at'], name='subscriptio_updated_3fe68c_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['uuid'], name='subscriptio_uuid_b39d17_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['created_at'], name='subscriptio_created_fce9c6_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['updated_at'], name='subscriptio_updated_95603e_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['name'], name='subscriptio_name_a325f2_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['is_active'], name='subscriptio_is_acti_b5f26e_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['active_since'], name='subscriptio_active__464b18_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['inactive_since'], name='subscriptio_inactiv_333b0e_idx'),
        ),
    ]