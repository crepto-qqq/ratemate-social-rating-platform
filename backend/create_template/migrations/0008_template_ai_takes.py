from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('create_template', '0007_template_is_hidden'),
    ]

    operations = [
        migrations.AddField(
            model_name='template',
            name='ai_takes',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
