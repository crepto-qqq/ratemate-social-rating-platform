from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [('accounts', '0003_user_profile_user')]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actor_name', models.CharField(blank=True, max_length=30)),
                ('kind', models.CharField(max_length=30)),
                ('target_type', models.CharField(max_length=20)),
                ('target_id', models.PositiveBigIntegerField()),
                ('source_id', models.PositiveBigIntegerField(blank=True, null=True)),
                ('action', models.CharField(blank=True, max_length=20)),
                ('summary', models.CharField(max_length=200)),
                ('preview', models.CharField(blank=True, max_length=160)),
                ('reason', models.CharField(blank=True, max_length=1000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_notifications', to='accounts.user_profile')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='accounts.user_profile')),
            ],
            options={
                'ordering': ['-created_at', '-id'],
                'indexes': [models.Index(fields=['recipient', '-created_at', '-id'], name='notification_feed')],
                'constraints': [models.UniqueConstraint(condition=Q(source_id__isnull=False), fields=('kind', 'source_id'), name='unique_notification_source')],
            },
        ),
    ]
