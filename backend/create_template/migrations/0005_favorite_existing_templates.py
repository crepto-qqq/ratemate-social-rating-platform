from django.db import migrations


def favorite_existing_templates(apps, schema_editor):
    Template = apps.get_model('create_template', 'Template')
    Favorite = apps.get_model('create_template', 'Favorite')
    Favorite.objects.bulk_create(
        [Favorite(user_id=template.owner_id, template_id=template.id) for template in Template.objects.all()],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('create_template', '0004_favorite'),
    ]

    operations = [
        migrations.RunPython(favorite_existing_templates, migrations.RunPython.noop),
    ]
