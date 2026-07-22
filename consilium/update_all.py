#!/usr/bin/env python3
"""
Обновляет модели модульных провайдеров (providers/*.py).
Перебирает все ключи, фильтрует по правилам, обновляет models в каждом файле.
Cron: 0 3 * * *
"""
import json, os, re, time, requests
from pathlib import Path

PROVIDERS_DIR = Path(__file__).parent / 'providers'
SERVER_DB = Path.home() / '.hermes' / 'skills' / 'consilium' / 'consilium_server.py'

# Правила фильтрации для каждого провайдера
RULES = {
    'openrouter': {
        'filter': lambda m: (
            ':free' in m.get('id', '') and
            m.get('context_length', 0) >= 128000 and
            not any(x in m.get('id', '').lower() for x in ['safety', 'guard', 'embed', 'vision', 'vl', 'image', 'audio', 'tts'])
        ),
        'sort': lambda m: -m.get('context_length', 0),
    },
    'groq': {
        'filter': lambda m: (
            any(x in m['id'].lower() for x in ['llama', 'mixtral', 'gemma']) and
            not any(x in m.get('id', '').lower() for x in ['deprecated', 'guard', 'embed', 'vision', 'audio'])
        ),
        'max': 5,
    },
    'hf': {
        'filter': lambda m: (
            any(x in m['id'].lower() for x in ['llama', 'mistral', 'qwen', 'gemma']) and
            not any(x in m.get('id', '').lower() for x in ['embed', 'vision', 'image', 'guard', 'safety'])
        ),
        'max': 5,
    },
    'github': {
        'filter': lambda m: not any(x in m.get('id', '').lower() for x in ['embed', 'vision', 'image', 'tts']),
        'max': 3,
    },
    'mistral': {
        'filter': lambda m: (
            any(x in m['id'].lower() for x in ['large', 'small', 'codestral']) and
            not any(x in m.get('id', '').lower() for x in ['embed', 'vision', 'image'])
        ),
        'max': 5,
    },
    'sambanova': {
        'filter': lambda m: not any(x in m.get('id', '').lower() for x in ['embed', 'vision', 'guard']),
        'max': 3,
    },
    'siliconflow': {
        'filter': lambda m: not any(x in m.get('id', '').lower() for x in ['embed', 'vision', 'image', 'tts', 'voice', 'audio']),
        'max': 5,
    },
    'reka': {
        'filter': lambda m: not any(x in m.get('id', '').lower() for x in ['embed', 'vision', 'edge']),
        'max': 3,
    },
    'deepinfra': {
        'filter': lambda m: (
            any(x in m['id'].lower() for x in ['llama', 'mistral', 'qwen']) and
            not any(x in m.get('id', '').lower() for x in ['embed', 'vision', 'image', 'guard'])
        ),
        'max': 5,
    },
    'together': {
        'filter': lambda m: not any(x in m.get('id', '').lower() for x in ['embed', 'vision', 'image']),
        'max': 5,
    },
}

def load_env():
    env = {}
    env_file = PROVIDERS_DIR.parent / '.env'
    if env_file.exists():
        for line in open(env_file):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env

def get_all_keys(env, prefix):
    keys = []
    i = 1
    while True:
        k = env.get(f'{prefix}_{i}', '').strip()
        if not k:
            break
        if 'trial' not in k.lower():
            keys.append(k)
        i += 1
    return keys

def fetch_models(url, key):
    try:
        r = requests.get(f'{url}/models', headers={'Authorization': f'Bearer {key}'}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            models = data.get('data', data) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            return [m if isinstance(m, dict) else {'id': str(m)} for m in models]
    except:
        pass
    return None

def try_all_keys(keys, url):
    for key in keys:
        time.sleep(0.3)
        models = fetch_models(url, key)
        if models:
            return models
    return None

def fetch_cloudflare_models(keys, account_id):
    """Cloudflare AI Models Search API"""
    for key in keys:
        time.sleep(0.3)
        try:
            r = requests.get(
                f'https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/models/search',
                headers={'Authorization': f'Bearer {key}'},
                timeout=15
            )
            if r.status_code == 200:
                result = r.json().get('result', [])
                # Cloudflare возвращает список строк (имена моделей) или объектов
                if result and isinstance(result[0], str):
                    return result[:10]
                elif result and isinstance(result[0], dict):
                    return [m.get('name', m.get('id', str(m))) for m in result[:10]]
                return []
        except:
            pass
    return None

def apply_rules(name, models):
    rule = RULES.get(name, {})
    if not models:
        return []
    
    # Фильтр
    filter_fn = rule.get('filter')
    if filter_fn:
        models = [m for m in models if filter_fn(m)]
    
    # Сортировка
    sort_fn = rule.get('sort')
    if sort_fn:
        models.sort(key=sort_fn)
    
    # Ограничение
    max_n = rule.get('max')
    if max_n:
        models = models[:max_n]
    
    return [m['id'] if isinstance(m, dict) else str(m) for m in models]

def update_provider_file(name, models, enabled):
    provider_file = PROVIDERS_DIR / f'{name}.py'
    if not provider_file.exists():
        return
    
    with open(provider_file) as f:
        code = f.read()
    
    code = re.sub(
        r'models = \[.*?\]',
        f'models = {json.dumps(models)}',
        code,
        flags=re.DOTALL
    )
    
    with open(provider_file, 'w') as f:
        f.write(code)

def update_task_map(all_models):
    with open(SERVER_DB) as f:
        code = f.read()
    
    code_m = [m for m in all_models if any(x in m.lower() for x in ['coder', 'deepseek'])][:3]
    analysis_m = [m for m in all_models if any(x in m.lower() for x in ['large', 'ultra', 'r1'])][:3]
    chat_m = [m for m in all_models if 'llama' in m.lower() and 'guard' not in m.lower()][:3]
    
    if code_m:
        code = re.sub(r'"code": \[.*?\]', f'"code": {json.dumps(code_m)}', code)
    if analysis_m:
        code = re.sub(r'"analysis": \[.*?\]', f'"analysis": {json.dumps(analysis_m)}', code)
    if chat_m:
        code = re.sub(r'"chat": \[.*?\]', f'"chat": {json.dumps(chat_m)}', code)
    
    with open(SERVER_DB, 'w') as f:
        f.write(code)
    print(f'✅ TASK_MODEL_MAP: code={code_m}, analysis={analysis_m}, chat={chat_m}')

# === MAIN ===
if __name__ == '__main__':
    env = load_env()
    print('=== ОБНОВЛЕНИЕ МОДЕЛЕЙ ===')
    
    all_models = []
    provider_configs = {
        'openrouter':    'OPENROUTER_API_KEY',
        'groq':          'GROQ_API_KEY',
        'mistral':       'MISTRAL_API_KEY',
        'github':        'GITHUB_TOKEN',
        'sambanova':     'SAMBANOVA_API_KEY',
        'hf':            'HF_TOKEN',
        'siliconflow':   'SILICONFLOW_API_KEY',
        'reka':          'REKA_API_KEY',
        'deepinfra':     'DEEPINFRA_API_KEY',
        'together':      'TOGETHER_API_KEY',
    }
    
    base_urls = {
        'openrouter':    'https://openrouter.ai/api/v1',
        'groq':          'https://api.groq.com/openai/v1',
        'mistral':       'https://api.mistral.ai/v1',
        'github':        'https://models.inference.ai.azure.com',
        'sambanova':     'https://api.sambanova.ai/v1',
        'hf':            'https://router.huggingface.co/v1',
        'siliconflow':   'https://api.siliconflow.cn/v1',
        'reka':          'https://api.reka.ai/v1',
        'deepinfra':     'https://api.deepinfra.com/v1/openai',
        'together':      'https://api.together.xyz/v1',
    }
    
    for name, prefix in provider_configs.items():
        keys = get_all_keys(env, prefix)
        if not keys:
            print(f'  ⏭️  {name}: нет ключей')
            continue
        
        models = try_all_keys(keys, base_urls[name])
        if not models:
            print(f'  ❌ {name}: API не ответил')
            continue
        
        filtered = apply_rules(name, models)
        update_provider_file(name, filtered, True)
        all_models.extend(filtered)
        print(f'  ✅ {name}: {len(filtered)}/{len(models)} моделей ({len(keys)} ключей)')
    
    # Cloudflare — через AI Models Search API
    cf_account = env.get('CLOUDFLARE_ACCOUNT_ID_1', '')
    cf_keys = get_all_keys(env, 'CLOUDFLARE_API_KEY')
    if cf_account and cf_keys:
        cf_models = fetch_cloudflare_models(cf_keys, cf_account)
        if cf_models:
            update_provider_file('cloudflare', cf_models, True)
            all_models.extend(cf_models)
            print(f'  ✅ cloudflare: {len(cf_models)} бесплатных моделей ({len(cf_keys)} ключей)')
        else:
            print(f'  ❌ cloudflare: API не ответил')
    else:
        print(f'  ⏭️  cloudflare: нет ключей или account_id')
    
    update_task_map(all_models)
    print(f'✅ Готово: {len(all_models)} моделей всего')
