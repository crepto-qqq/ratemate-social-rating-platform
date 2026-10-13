from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('create_template', '0006_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='template',
            name='is_hidden',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
