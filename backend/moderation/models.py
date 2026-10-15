from django.conf import settings
from django.db import models


class ModerationAction(models.Model):
    HIDE_TEMPLATE = 'hide_template'
    RESTORE_TEMPLATE = 'restore_template'
    REMOVE_RATING = 'remove_rating'
    REMOVE_TEMPLATE_COMMENT = 'remove_template_comment'
    REMOVE_RATING_COMMENT = 'remove_rating_comment'

    ACTION_CHOICES = [
        (HIDE_TEMPLATE, 'Hide template'),
        (RESTORE_TEMPLATE, 'Restore template'),
        (REMOVE_RATING, 'Remove public rating'),
        (REMOVE_TEMPLATE_COMMENT, 'Remove template comment'),
        (REMOVE_RATING_COMMENT, 'Remove rating comment'),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='moderation_actions',
    )
    actor_name = models.CharField(max_length=150)
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=16)
    target_id = models.PositiveBigIntegerField()
    target_label = models.CharField(max_length=200)
    reason = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.action}: {self.target_type} #{self.target_id}'
