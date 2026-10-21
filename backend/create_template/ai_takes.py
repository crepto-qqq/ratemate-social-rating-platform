import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


logger = logging.getLogger(__name__)


class AIRatingError(Exception):
    pass


def _schema(template):
    pair_count = template.items.count() * template.criteria.count()
    return {
        'type': 'object',
        'properties': {
            'scores': {
                'type': 'array',
                'minItems': pair_count,
                'maxItems': pair_count,
                'items': {
                    'type': 'object',
                    'properties': {
                        'itemId': {
                            'type': 'integer',
                            'enum': list(template.items.values_list('id', flat=True)),
                        },
                        'criterionId': {
                            'type': 'integer',
                            'enum': list(template.criteria.values_list('id', flat=True)),
                        },
                        'score': {'type': 'integer', 'minimum': 1, 'maximum': 5},
                    },
                    'required': ['itemId', 'criterionId', 'score'],
                    'additionalProperties': False,
                },
            },
        },
        'required': ['scores'],
        'additionalProperties': False,
    }


def _prompt(template):
    context = {
        'title': template.title,
        'description': template.description,
        'criteria': [
            {'id': criterion.id, 'name': criterion.name, 'weight': criterion.weight}
            for criterion in template.criteria.all()
        ],
        'items': [
            {'id': item.id, 'name': item.name}
            for item in template.items.all()
        ],
    }
    return (
        'Create a subjective, creative AI rating for this template. Score every item against '
        'every criterion from 1 to 5, using only the supplied IDs. Return exactly one score for '
        'each item-criterion pair. Use the title, description, item names, criterion names, and '
        'weights as context; make useful distinctions and avoid ties when reasonable.\n\n'
        f'Template data:\n{json.dumps(context, ensure_ascii=False)}'
    )


def _output_text(response_data):
    for output in response_data.get('output', []):
        if output.get('type') != 'message':
            continue
        for content in output.get('content', []):
            if content.get('type') == 'output_text' and isinstance(content.get('text'), str):
                return content['text']
            if content.get('type') == 'refusal':
                raise AIRatingError('AI 无法为此模板生成评分。')
    raise AIRatingError('AI 服务没有返回评分结果。')


def validate_ai_scores(template, raw_scores):
    if not isinstance(raw_scores, list):
        raise AIRatingError('AI 返回了无效的评分格式。')
    expected_pairs = {
        (item_id, criterion_id)
        for item_id in template.items.values_list('id', flat=True)
        for criterion_id in template.criteria.values_list('id', flat=True)
    }
    received_pairs = set()
    normalized = []
    for entry in raw_scores:
        if not isinstance(entry, dict):
            raise AIRatingError('AI 返回了无效的评分条目。')
        item_id = entry.get('itemId')
        criterion_id = entry.get('criterionId')
        score = entry.get('score')
        pair = (item_id, criterion_id)
        if (
            type(item_id) is not int
            or type(criterion_id) is not int
            or type(score) is not int
            or pair not in expected_pairs
            or pair in received_pairs
            or not 1 <= score <= 5
        ):
            raise AIRatingError('AI 返回了不完整或无效的评分。')
        received_pairs.add(pair)
        normalized.append({'itemId': item_id, 'criterionId': criterion_id, 'score': score})
    if received_pairs != expected_pairs:
        raise AIRatingError('AI 没有完成全部评分。')
    return normalized


def generate_ai_take_scores(template):
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise AIRatingError('尚未配置 OPENAI_API_KEY。')

    payload = {
        'model': settings.OPENAI_MODEL,
        'store': False,
        'input': [
            {
                'role': 'system',
                'content': 'You create fair, thoughtful ratings and return only the requested structure.',
            },
            {'role': 'user', 'content': _prompt(template)},
        ],
        'text': {
            'format': {
                'type': 'json_schema',
                'name': 'template_ai_rating',
                'strict': True,
                'schema': _schema(template),
            },
        },
        'max_output_tokens': min(10000, max(500, template.items.count() * template.criteria.count() * 40)),
    }
    request = Request(
        'https://api.openai.com/v1/responses',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urlopen(request, timeout=settings.OPENAI_TIMEOUT) as response:
            response_data = json.loads(response.read().decode('utf-8'))
        parsed = json.loads(_output_text(response_data))
    except HTTPError as error:
        logger.warning('OpenAI API returned HTTP %s', error.code)
        raise AIRatingError('AI 评分服务暂时不可用，请稍后重试。') from error
    except (URLError, TimeoutError) as error:
        logger.warning('OpenAI API request failed: %s', type(error).__name__)
        raise AIRatingError('无法连接 AI 评分服务，请稍后重试。') from error
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
        logger.warning('OpenAI API returned an invalid response')
        raise AIRatingError('AI 返回了无法读取的评分结果。') from error

    return validate_ai_scores(template, parsed.get('scores'))
