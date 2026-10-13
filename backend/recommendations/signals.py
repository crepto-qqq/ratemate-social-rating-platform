from uuid import uuid4
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from create_template.models import Template, Criterion, Item
from .models import TemplateEmbedding

def queue_template(template_id):
    if not Template.objects.filter(pk=template_id).exists():
        return
    embedding, _ = TemplateEmbedding.objects.get_or_create(template_id=template_id)
    TemplateEmbedding.objects.filter(pk=embedding.pk).update(
        token=uuid4(), status='pending', vector=None, retry_at=None, error='', updated_at=timezone.now())

@receiver(post_save, sender=Template)
def template_changed(sender, instance, raw=False, **kwargs):
    # Moderation visibility changes do not alter the embedding's source text.
    update_fields = kwargs.get('update_fields')
    if not raw and (update_fields is None or not set(update_fields) <= {'is_hidden', 'updated_at'}):
        queue_template(instance.pk)

@receiver(post_save, sender=Criterion)
@receiver(post_save, sender=Item)
@receiver(post_delete, sender=Criterion)
@receiver(post_delete, sender=Item)
def content_changed(sender, instance, **kwargs):
    origin = kwargs.get('origin')
    origin_model = getattr(origin, 'model', type(origin))
    # Cascading deletion must not recreate an embedding for a deleted template.
    if kwargs.get('signal') is post_delete and origin_model not in (Criterion, Item):
        return
    if not kwargs.get('raw'):
        queue_template(instance.template_id)
