import logging
import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import close_old_connections, transaction
from django.db.models import Q
from django.utils import timezone
from create_template.models import Template
from recommendations.embedding import MODEL, content_hash, embed_text, template_text
from recommendations.models import TemplateEmbedding
from recommendations.signals import queue_template

logger = logging.getLogger(__name__)

def process_next():
    now = timezone.now()
    TemplateEmbedding.objects.filter(status='processing', updated_at__lt=now - timedelta(minutes=10)).update(status='pending')
    with transaction.atomic():
        job = TemplateEmbedding.objects.select_for_update(skip_locked=True).filter(
            Q(status='pending') | Q(status='error', retry_at__lte=now)).order_by('updated_at').first()
        if job is None:
            return False
        token, job_id, template_id = job.token, job.pk, job.template_id
        TemplateEmbedding.objects.filter(pk=job_id).update(status='processing', updated_at=now)
    try:
        template = Template.objects.prefetch_related('criteria', 'items').get(pk=template_id)
        text = template_text(template)
        vector = embed_text(text)
        updated = TemplateEmbedding.objects.filter(pk=job_id, token=token).update(
            vector=vector, model=MODEL, content_hash=content_hash(text), status='ready',
            error='', retry_at=None, updated_at=timezone.now())
        if updated:
            logger.info('Generated embedding for template %s', template_id)
    except Template.DoesNotExist:
        pass
    except Exception as error:
        logger.exception('Embedding failed for template %s', template_id)
        TemplateEmbedding.objects.filter(pk=job_id, token=token).update(
            status='error', error=str(error)[:1000], retry_at=timezone.now() + timedelta(minutes=5), updated_at=timezone.now())
    return True

class Command(BaseCommand):
    help = 'Generate local semantic embeddings. --watch runs the background worker.'

    def add_arguments(self, parser):
        parser.add_argument('--watch', action='store_true')
        parser.add_argument('--rebuild', action='store_true')

    def handle(self, *args, **options):
        for template_id in Template.objects.values_list('id', flat=True).iterator():
            embedding, _ = TemplateEmbedding.objects.get_or_create(template_id=template_id)
            if options['rebuild'] or (embedding.status == 'ready' and embedding.model != MODEL):
                queue_template(template_id)
        while True:
            close_old_connections()
            processed = process_next()
            if not options['watch'] and not processed:
                return
            if not processed:
                time.sleep(5)
