from django.db import models
from django.db.models import Q

from accounts.models import User_profile


class Notification(models.Model):
    """A recipient-owned snapshot of an interaction or moderation action."""

    TEMPLATE_FAVORITE = 'template_favorite'
    TEMPLATE_COMMENT = 'template_comment'
    RATING_LIKE = 'rating_like'
    RATING_COMMENT = 'rating_comment'
    MODERATION = 'moderation'
    INTERACTION_KINDS = (
        TEMPLATE_FAVORITE, TEMPLATE_COMMENT, RATING_LIKE, RATING_COMMENT,
    )

    recipient = models.ForeignKey(
        User_profile, on_delete=models.CASCADE, related_name='notifications',
    )
    actor = models.ForeignKey(
        User_profile, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='sent_notifications',
    )
    actor_name = models.CharField(max_length=30, blank=True)
    kind = models.CharField(max_length=30)
    # Interaction targets are templates or public ratings. Moderation targets may
    # have been removed; their title is kept in summary, without the removed body.
    target_type = models.CharField(max_length=20)
    target_id = models.PositiveBigIntegerField()
    source_id = models.PositiveBigIntegerField(null=True, blank=True)
    action = models.CharField(max_length=20, blank=True)
    summary = models.CharField(max_length=200)
    preview = models.CharField(max_length=160, blank=True)
    reason = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recipient', '-created_at', '-id'], name='notification_feed')]
        constraints = [
            models.UniqueConstraint(
                fields=['kind', 'source_id'], condition=Q(source_id__isnull=False),
                name='unique_notification_source',
            ),
        ]
