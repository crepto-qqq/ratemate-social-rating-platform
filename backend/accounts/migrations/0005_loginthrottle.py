from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [('accounts', '0004_accountsecurity_otpchallenge')]
    operations = [
        migrations.CreateModel(
            name='LoginThrottle',
            fields=[
                ('key', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('window_started_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
    ]
