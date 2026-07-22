from .base import BaseProvider, ProviderConfig
import httpx, json, time, logging

logger = logging.getLogger("consilium")

class OpenAICompatProvider(BaseProvider):
    async def chat_completion(self, messages, model, **kwargs) -> dict:
        payload = {"model": model, "messages": self._norm(messages)}
        payload.update({k: v for k, v in kwargs.items() if v is not None and k not in ['model','messages']})
        
        resp = await self.client.post("/chat/completions", json=payload, headers={
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        })
        resp.raise_for_status()
        return self._norm_response(resp.json())
    
    async def stream_completion(self, messages, model, **kwargs):
        payload = {"model": model, "messages": self._norm(messages), "stream": True}
        
        async with self.client.stream("POST", "/chat/completions", json=payload, headers={
            "Authorization": f"Bearer {self.config.api_key}"
        }) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    d = line[6:]
                    if d == "[DONE]": break
                    try:
                        chunk = json.loads(d)
                        yield self._norm_chunk(chunk)
                    except: continue
    
    async def list_models(self) -> list:
        resp = await self.client.get("/models", headers={"Authorization": f"Bearer {self.config.api_key}"})
        return resp.json().get("data", []) if resp.status_code == 200 else []
    
    def _norm(self, messages):
        return [{"role": m.get("role","user"), "content": m.get("content","") if isinstance(m.get("content"), str) else "".join(b.get("text","") for b in m["content"] if b.get("type")=="text")} for m in messages]
    
    def _norm_response(self, data):
        c = data.get("choices",[{}])[0]
        msg = c.get("message",{})
        content = msg.get("content","")
        if content is None: content = ""
        if isinstance(content, list): content = "".join(b.get("text","") for b in content)
        result = {
            "id": data.get("id", f"gen-{int(time.time())}"),
            "object": "chat.completion", "created": int(time.time()),
            "model": data.get("model","auto"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": c.get("finish_reason") or "stop"}],
            "usage": data.get("usage", {"prompt_tokens":0,"completion_tokens":0,"total_tokens":0})
        }
        if msg.get("tool_calls"): result["choices"][0]["message"]["tool_calls"] = msg["tool_calls"]
        return result
    
    def _norm_chunk(self, chunk):
        c = chunk.get("choices",[{}])[0]
        d = c.get("delta",{})
        return {"id": chunk.get("id"), "object": "chat.completion.chunk", "created": chunk.get("created", int(time.time())), "model": chunk.get("model",""), "choices": [{"index": 0, "delta": {"content": d.get("content",""), "role": d.get("role")}, "finish_reason": c.get("finish_reason")}]}
