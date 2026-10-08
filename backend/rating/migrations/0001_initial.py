from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0002_user_profile_username'),
        ('create_template', '0003_delete_rating'),
    ]

    operations = [
        migrations.CreateModel(
            name='RatingResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rating_results', to='accounts.user_profile')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rating_results', to='create_template.template')),
            ],
        ),
        migrations.CreateModel(
            name='RatingScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('criterion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rating_scores', to='create_template.criterion')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rating_scores', to='create_template.item')),
                ('result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scores', to='rating.ratingresult')),
            ],
        ),
        migrations.AddConstraint(
            model_name='ratingscore',
            constraint=models.UniqueConstraint(fields=('result', 'item', 'criterion'), name='unique_score_per_result_item_criterion'),
        ),
    ]
