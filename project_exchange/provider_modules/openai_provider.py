from __future__ import annotations

import json
import urllib.request

from project_exchange.config import secret, status_for_key


class OpenAIReasoningProvider:
    name = "OpenAI"
    env_var = "OPENAI_API_KEY"

    def status(self):
        return status_for_key(self.name, self.env_var, ("sk-",), 20)

    def reason(self, prompt: str, payload: dict[str, object]) -> dict[str, object]:
        api_key = secret(self.env_var)
        if not api_key:
            raise RuntimeError("OpenAI provider is disconnected")
        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Return concise JSON only."},
                {"role": "user", "content": prompt + "\n\nPayload:\n" + json.dumps(payload, ensure_ascii=False)},
            ],
            "temperature": 0.1,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {"reasoning": content}
        parsed["provider"] = self.name
        return parsed
