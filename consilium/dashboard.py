"""Dashboard — веб-интерфейс Consilium v8."""
from fastapi.responses import HTMLResponse
import time

async def dashboard_html(providers, rate_limiter):
    rows = []
    for p in providers:
        name = p.get("name", "?")
        keys = len(p.get("keys", []))
        keyless = p.get("keyless", False)
        available, reason = rate_limiter.is_available(name, 0) if rate_limiter else (True, None)
        status = "✅" if (available and (keys > 0 or keyless)) else "❌"
        rows.append(f"<tr><td>{name}</td><td>{keys}</td><td>{status}</td><td>{reason or 'OK'}</td></tr>")
    
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>Consilium v8</title><meta charset="utf-8">
<style>body{{font-family:Arial;margin:20px}}table{{border-collapse:collapse}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#4CAF50;color:white}}tr:nth-child(even){{background:#f2f2f2}}</style></head>
<body><h1>🚀 Consilium v8</h1><p>Ключи и fallback — в Hermes. Consilium — фильтр + роутер.</p>
<h2>Провайдеры</h2><table><tr><th>Provider</th><th>Keys</th><th>Status</th><th>Info</th></tr>
{''.join(rows)}</table>
<p>Updated: {time.strftime('%H:%M:%S')}</p></body></html>""")
