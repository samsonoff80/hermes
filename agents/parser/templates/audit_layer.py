#!/usr/bin/env python3
"""Consilium Layer Auditor — template for auditing pipeline layers"""
import asyncio, aiohttp, os, sys, json, re

sys.path.insert(0, os.path.expanduser("~/.hermes/skills/consilium"))
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/.hermes/.env"))
from providers import consilium_ask, CONSILIUM_MODELS

# === CONFIGURE ===
LAYER_NAME = "Layer X"
PROMPT = """You are a B2B data expert. Audit the {layer_name} scripts.

[Describe what the scripts do]

EVALUATION CRITERIA:
1. What works well?
2. What should be fixed/removed?
3. What's missing?
4. Any bugs?

Answer ONLY JSON: {{"fixes":[...],"removals":[...],"additions":[...],"bugs":[...],"score_1_to_5":N}}"""
# === END CONFIG ===

async def main():
    models = [m[0] for m in CONSILIUM_MODELS]
    async with aiohttp.ClientSession() as session:
        result = await consilium_ask(session, PROMPT, models=models)
        
        print(f"\n{'='*60}")
        print(f"  {LAYER_NAME} — Consilium Audit")
        print(f"  Models responded: {len(result.get('responses',{}))}/{len(models)}")
        print(f"  All agree: {result.get('all_agree', False)}")
        print(f"{'='*60}\n")
        
        best = result.get('best', '')
        print(f"Best answer ({len(best)} chars):")
        print(best[:2000])
        
        # Try to extract JSON
        try:
            json_str = re.search(r'\{.*\}', best, re.DOTALL).group()
            data = json.loads(json_str)
            print(f"\nParsed JSON keys: {list(data.keys())}")
            print(f"Score: {data.get('score_1_to_5', '?')}")
        except:
            print("\nCould not parse JSON from response")

asyncio.run(main())
