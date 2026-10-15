from .models import Notification


def notify_interaction(recipient, actor, kind, source_id, target_type, target_id, summary, preview=''):
    """Create one notification for a newly created interaction, excluding self actions."""
    if recipient.pk == actor.pk:
        return None
    notification, _ = Notification.objects.get_or_create(
        kind=kind,
        source_id=source_id,
        defaults={
            'recipient': recipient,
            'actor': actor,
            'actor_name': actor.userName,
            'target_type': target_type,
            'target_id': target_id,
            'summary': summary[:200],
            'preview': preview[:160],
        },
    )
    return notification


def remove_interaction_notification(kind, source_id):
    Notification.objects.filter(kind=kind, source_id=source_id).delete()


def remove_comment_notification(kind, comment_id):
    """Remove a comment's interaction notice when that comment is removed."""
    if kind not in (Notification.TEMPLATE_COMMENT, Notification.RATING_COMMENT):
        raise ValueError('Expected template_comment or rating_comment.')
    remove_interaction_notification(kind, comment_id)


def update_comment_notification(kind, comment_id, content):
    if kind not in (Notification.TEMPLATE_COMMENT, Notification.RATING_COMMENT):
        raise ValueError('Expected template_comment or rating_comment.')
    Notification.objects.filter(kind=kind, source_id=comment_id).update(preview=content[:160])


def remove_interaction_notifications(content_type, content_id, kinds=None):
    """Clear interactions pointing at content that is now inaccessible."""
    if content_type not in ('template', 'rating'):
        raise ValueError('Expected template or rating.')
    queryset = Notification.objects.filter(
        target_type=content_type,
        target_id=content_id,
        kind__in=Notification.INTERACTION_KINDS,
    )
    if kinds is not None:
        queryset = queryset.filter(kind__in=kinds)
    queryset.delete()


def notify_moderation(recipient, action, content_type, content_id, summary, reason):
    """Persist a moderation notice even if the affected content is later deleted.

    Admin views own authorization and audit records. This service stores no admin
    identity and no removed body/image. It deliberately allows repeated actions.
    """
    if action not in ('removed', 'hidden', 'restored'):
        raise ValueError('Unsupported moderation action.')
    if content_type not in ('template', 'rating', 'comment'):
        raise ValueError('Unsupported moderation content type.')
    return Notification.objects.create(
        recipient=recipient,
        kind=Notification.MODERATION,
        action=action,
        target_type=content_type,
        target_id=content_id,
        summary=summary[:200],
        reason=reason[:1000],
    )
