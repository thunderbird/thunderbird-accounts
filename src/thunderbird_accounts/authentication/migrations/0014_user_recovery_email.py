from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0013_alter_user_plan_allowlistentry'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='recovery_email',
            field=models.CharField(help_text='The recovery email associated with this account', max_length=256, null=True),
        ),
    ]
