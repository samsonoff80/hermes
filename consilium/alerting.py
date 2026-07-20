#!/usr/bin/env python3
"""Alerting — уведомления в Telegram при критических событиях."""
import httpx, logging, os

logger = logging.getLogger("consilium.alerts")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")

async def send_alert(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT, "text": f"🚨 Consilium Alert\n{message}"}
            )
    except Exception as e:
        logger.warning(f"Failed to send alert: {e}")

async def alert_all_providers_down():
    await send_alert("⚠️ All providers are DOWN!")

async def alert_provider_disabled(provider, reason):
    await send_alert(f"❌ {provider} disabled: {reason}")

async def alert_circuit_breaker(provider):
    await send_alert(f"🔴 {provider}: circuit breaker OPEN")
