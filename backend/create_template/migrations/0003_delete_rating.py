from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('create_template', '0002_alter_item_image'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Rating',
        ),
    ]
