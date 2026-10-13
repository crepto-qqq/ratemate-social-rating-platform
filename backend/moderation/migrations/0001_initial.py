import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('create_template', '0007_template_is_hidden'),
        ('rating', '0003_ratingresultcomment_ratingresultlike'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModerationAction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actor_name', models.CharField(max_length=150)),
                ('action', models.CharField(choices=[('hide_template', 'Hide template'), ('restore_template', 'Restore template'), ('remove_rating', 'Remove public rating'), ('remove_template_comment', 'Remove template comment'), ('remove_rating_comment', 'Remove rating comment')], max_length=32)),
                ('target_type', models.CharField(max_length=16)),
                ('target_id', models.PositiveBigIntegerField()),
                ('target_label', models.CharField(max_length=200)),
                ('reason', models.CharField(max_length=1000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='moderation_actions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
    ]
