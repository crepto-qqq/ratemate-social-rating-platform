from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from accounts.models import User_profile
from create_template.models import Criterion, Item, Template


class RatingResult(models.Model):
    id = models.BigAutoField(
        auto_created=True,
        primary_key=True,
        serialize=False,
        verbose_name='ID',
    )
    owner = models.ForeignKey(
        User_profile,
        on_delete=models.CASCADE,
        related_name='rating_results',
    )
    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        related_name='rating_results',
    )
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.owner.userName} - {self.template.title}'


class RatingScore(models.Model):
    result = models.ForeignKey(
        RatingResult,
        on_delete=models.CASCADE,
        related_name='scores',
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='rating_scores',
    )
    criterion = models.ForeignKey(
        Criterion,
        on_delete=models.CASCADE,
        related_name='rating_scores',
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['result', 'item', 'criterion'],
                name='unique_score_per_result_item_criterion',
            ),
        ]

    def clean(self):
        super().clean()
        if not self.result_id or not self.item_id or not self.criterion_id:
            return
        template_id = self.result.template_id
        if self.item.template_id != template_id:
            raise ValidationError('Item must belong to the selected template.')
        if self.criterion.template_id != template_id:
            raise ValidationError('Criterion must belong to the selected template.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.item} - {self.criterion}: {self.score}'
