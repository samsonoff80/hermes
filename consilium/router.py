#!/usr/bin/env python3
"""Consilium Router — логика маршрутизации и формирования ответа."""
import re, json, time, hashlib, logging
from typing import Optional

logger = logging.getLogger('consilium.router')

def classify_task(messages: list) -> str:
    user_text = ([m.get('content', '') for m in messages if m.get('role') == 'user'] or [''])[-1].lower()
    if any(kw in user_text for kw in ['найди', 'поиск', 'спарси', 'url', 'http']):
        return 'search'
    elif any(kw in user_text for kw in ['код', 'code', 'python', 'функци', 'script']):
        return 'code'
    elif any(kw in user_text for kw in ['анализ', 'сравни', 'статус', 'почем']):
        return 'analysis'
    return 'chat'

def build_response(provider_resp: dict, target_provider: dict, target_model: str, start_time: float) -> dict:
    content = None
    tool_calls = []
    usage = provider_resp.get('usage', {})
    finish_reason = 'stop'
    
    if 'choices' in provider_resp and provider_resp['choices']:
        msg = provider_resp['choices'][0].get('message', {})
        content = msg.get('content')
        tool_calls = msg.get('tool_calls', [])
        finish_reason = provider_resp['choices'][0].get('finish_reason', 'stop')
    
    message = {'role': 'assistant', 'content': content, 'tool_calls': tool_calls}
    
    return {
        'id': f"chatcmpl-{hashlib.md5(str(time.time()).encode()).hexdigest()[:12]}",
        'object': 'chat.completion',
        'created': int(time.time()),
        'model': target_model,
        'choices': [{'index': 0, 'message': message, 'finish_reason': finish_reason}],
        'usage': usage
    }
