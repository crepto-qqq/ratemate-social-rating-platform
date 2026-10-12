import hashlib
import math
from functools import lru_cache
from django.conf import settings

MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
DIMENSIONS = 384

def normalized(vector):
    values = [float(value) for value in vector]
    length = math.sqrt(sum(value * value for value in values))
    if not length or not all(math.isfinite(value) for value in values):
        return None
    return [value / length for value in values]

def template_text(template):
    criteria = '; '.join(c.name for c in template.criteria.all())
    items = '; '.join(item.name for item in template.items.all())
    return f'{template.title}\n{template.description}\nCriteria: {criteria}\nItems: {items}'

def content_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()

@lru_cache(maxsize=1)
def encoder():
    from fastembed import TextEmbedding
    return TextEmbedding(model_name=MODEL, cache_dir=settings.EMBEDDING_CACHE_DIR, threads=2)

def embed_text(text):
    vector = normalized(next(iter(encoder().embed([text]))))
    if vector is None or len(vector) != DIMENSIONS:
        raise ValueError('Embedding model returned an invalid vector.')
    return vector
