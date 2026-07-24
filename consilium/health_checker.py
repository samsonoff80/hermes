#!/usr/bin/env python3
"""Health Checker — заглушка."""
import logging
logger = logging.getLogger("consilium.health")

async def check_all_providers(providers):
    logger.info("🏥 Health check: skipped (stub)")
    return []
