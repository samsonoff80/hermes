#!/usr/bin/env python3
"""Dashboard — веб-интерфейс для мониторинга."""
from fastapi.responses import HTMLResponse
from provider_stats import provider_stats

async def dashboard_html(providers, rate_limiter):
    rows = []
    priority = provider_stats.get_priority()
    for p in providers:
        name = p["name"]
        keys = len(p.get("keys", []))
        keyless = p.get("keyless", False)
        available, reason = rate_limiter.is_available(name, 0)
        status = "✅" if (available and (keys > 0 or keyless)) else "❌"
        rows.append(f"<tr><td>{name}</td><td>{keys}</td><td>{status}</td><td>{reason or 'OK'}</td></tr>")
    
    html = f"""<!DOCTYPE html>
<html><head><title>Consilium v7</title>
<meta charset="utf-8"><style>body{{font-family:Arial;margin:20px}}table{{border-collapse:collapse}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#4CAF50;color:white}}tr:nth-child(even){{background:#f2f2f2}}</style></head>
<body><h1>🚀 Consilium v7</h1>
<h2>Провайдеры</h2><table><tr><th>Provider</th><th>Keys</th><th>Status</th><th>Info</th></tr>
{''.join(rows)}</table>
<h2>Приоритет (по успешности)</h2><table><tr><th>Provider</th><th>Success Rate</th><th>Avg Latency</th></tr>
{''.join(f'<tr><td>{p[0]}</td><td>{p[1]:.1%}</td><td>{p[2]:.1f}s</td></tr>' for p in priority)}</table>
<p>Updated: {__import__('datetime').datetime.now().strftime('%H:%M:%S')}</p></body></html>"""
    return HTMLResponse(content=html)
