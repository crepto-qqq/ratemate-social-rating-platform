from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('create_template', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='image',
            field=models.ImageField(upload_to='template_items/'),
        ),
    ]
