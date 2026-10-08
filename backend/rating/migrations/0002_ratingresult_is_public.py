from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rating', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ratingresult',
            name='is_public',
            field=models.BooleanField(default=False),
        ),
    ]
