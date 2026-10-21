from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from accounts.models import User_profile


class Template(models.Model):
    id = models.BigAutoField(
        auto_created=True,
        primary_key=True,
        serialize=False,
        verbose_name='ID',
    )
    owner = models.ForeignKey(
        User_profile,
        on_delete=models.CASCADE,
        related_name='templates',
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_hidden = models.BooleanField(default=False, db_index=True)
    ai_takes = models.JSONField(null=True, blank=True)
    criteria_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def popularity(self):
        return self.favorite_records.count()


class Criterion(models.Model):
    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        related_name='criteria',
    )
    name = models.CharField(max_length=100)
    weight = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['template', 'order'],
                name='unique_criterion_order_per_template',
            ),
        ]

    def clean(self):
        super().clean()
        if not self.template_id or not self.template.criteria_locked:
            return
        if self._state.adding:
            raise ValidationError('Criteria are locked for this template.')
        original = type(self).objects.get(pk=self.pk)
        if (self.name, self.weight, self.order) != (
            original.name,
            original.weight,
            original.order,
        ):
            raise ValidationError('Criteria are locked for this template.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.template.criteria_locked:
            raise ValidationError('Criteria are locked for this template.')
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.name


class Item(models.Model):
    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        related_name='items',
    )
    name = models.CharField(max_length=120)
    image = models.ImageField(upload_to='template_items/')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['template', 'order'],
                name='unique_item_order_per_template',
            ),
        ]

    def __str__(self):
        return self.name


class Favorite(models.Model):
    user = models.ForeignKey(
        User_profile,
        on_delete=models.CASCADE,
        related_name='favorite_records',
    )
    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        related_name='favorite_records',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'template'],
                name='unique_favorite_per_user_and_template',
            ),
        ]

    def __str__(self):
        return f'{self.user.userName} - {self.template.title}'


class Comment(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User_profile, on_delete=models.CASCADE, related_name='comments')
    content = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['template', '-created_at', '-id'], name='comment_template_newest')]
