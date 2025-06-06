# Generated by Django 5.2.1 on 2025-05-13 17:39

import django.db.models.deletion
import thunderbird_accounts.subscription.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscription', '0002_plan_price_subscriptionitem_remove_customer_user_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('paddle_id', thunderbird_accounts.subscription.models.PaddleId(db_index=True, default=None, help_text='The transaction paddle id.', max_length=256, null=True)),
                ('paddle_invoice_id', thunderbird_accounts.subscription.models.PaddleId(db_index=True, default=None, help_text='The invoice paddle id,', max_length=256, null=True)),
                ('paddle_subscription_id', thunderbird_accounts.subscription.models.PaddleId(db_index=True, default=None, help_text='The subscription paddle id.', max_length=256, null=True)),
                ('invoice_number', models.CharField(help_text='Invoice number for this transaction.', null=True)),
                ('total', models.CharField(help_text='Total after discount and tax.', max_length=256)),
                ('tax', models.CharField(help_text='Total tax on the subtotal.', max_length=256)),
                ('currency', models.CharField(help_text='Three letter ISO 4217 currency code.', max_length=256)),
                ('status', models.CharField(choices=[('', 'None'), ('draft', 'Draft'), ('ready', 'Ready'), ('billed', 'Billed'), ('paid', 'Paid'), ('completed', 'Completed'), ('canceled', 'Canceled'), ('past_due', 'Past Due')], default='', help_text='The current subscription status.', max_length=256)),
                ('transaction_origin', models.CharField(choices=[('', 'None'), ('api', 'Api'), ('subscription_charge', 'Subscription: Charge'), ('subscription_payment_method_change', 'Subscription: Payment method change'), ('subscription_recurring', 'Subscription: Recurring'), ('subscription_update', 'Subscription: Update'), ('web', 'Web')], default='', help_text='where the transaction first start from.')),
                ('billed_at', models.DateTimeField(help_text='date when the subscription is next schedule to be billed.', null=True)),
                ('revised_at', models.DateTimeField(help_text='date when the subscription is next schedule to be billed.', null=True)),
                ('webhook_updated_at', models.DateTimeField(help_text='date when this model was last updated by a paddle webhook.', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='transaction_origin',
        ),
        migrations.AddField(
            model_name='price',
            name='webhook_updated_at',
            field=models.DateTimeField(help_text='date when this model was last updated by a paddle webhook.', null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='webhook_updated_at',
            field=models.DateTimeField(help_text='date when this model was last updated by a paddle webhook.', null=True),
        ),
        migrations.AddIndex(
            model_name='price',
            index=models.Index(fields=['currency'], name='subscriptio_currenc_a8b539_idx'),
        ),
        migrations.AddIndex(
            model_name='price',
            index=models.Index(fields=['billing_cycle_frequency'], name='subscriptio_billing_eca2d3_idx'),
        ),
        migrations.AddIndex(
            model_name='price',
            index=models.Index(fields=['billing_cycle_interval'], name='subscriptio_billing_1a1d5c_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['next_billed_at'], name='subscriptio_next_bi_8da10c_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['current_billing_period_starts_at', 'current_billing_period_ends_at'], name='subscriptio_current_c16106_idx'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='subscription',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='subscription.subscription'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['uuid'], name='subscriptio_uuid_5e11b7_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['created_at'], name='subscriptio_created_f0cb0f_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['updated_at'], name='subscriptio_updated_2dd3b2_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['invoice_number'], name='subscriptio_invoice_7421c5_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['transaction_origin'], name='subscriptio_transac_a16acb_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['currency'], name='subscriptio_currenc_e9192e_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['status'], name='subscriptio_status_e6f399_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['billed_at'], name='subscriptio_billed__0d16a6_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['revised_at'], name='subscriptio_revised_1a6376_idx'),
        ),
    ]
