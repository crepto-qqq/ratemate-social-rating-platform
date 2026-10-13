from uuid import uuid4
from django.db import models
from pgvector.django import VectorField

class TemplateEmbedding(models.Model):
    template = models.OneToOneField('create_template.Template', on_delete=models.CASCADE, related_name='embedding')
    vector = VectorField(dimensions=384, null=True, blank=True)
    model = models.CharField(max_length=200, blank=True)
    content_hash = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=12, default='pending', db_index=True)
    token = models.UUIDField(default=uuid4)
    updated_at = models.DateTimeField(auto_now=True)
    retry_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

class UserPreference(models.Model):
    user = models.OneToOneField('accounts.User_profile', on_delete=models.CASCADE, related_name='recommendation_preference')
    vector = VectorField(dimensions=384, null=True, blank=True)
    fingerprint = models.CharField(max_length=64)
    updated_at = models.DateTimeField(auto_now=True)
