"""OpenAI chat completions over plain HTTPS (no SDK needed), JSON output, retries and a cost counter."""
import json
import os
import time
from dataclasses import dataclass, field

import requests


class LLMError(Exception):
    pass


@dataclass
class LLM:
    settings: dict
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    log: list = field(default_factory=list)

    @property
    def mode(self) -> str:
        return self.settings["llm"]["mode"]

    @property
    def ready(self) -> bool:
        return self.mode == "mock" or bool(os.getenv("OPENAI_API_KEY"))

    @property
    def cost_usd(self) -> float:
        s = self.settings["llm"]
        return (self.tokens_in * s["price_in"] + self.tokens_out * s["price_out"]) / 1e6

    def json(self, system: str, user: str, retries: int = 2) -> dict:
        if self.mode == "mock":
            raise LLMError("mock mode: use pinstudio.mock instead")
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise LLMError("No OPENAI_API_KEY found. Add it to the .env file, or set LLM_MODE=mock.")
        s = self.settings["llm"]
        body = {"model": s["model"], "temperature": s["temperature"], "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        last = None
        for attempt in range(retries + 1):
            try:
                r = requests.post(f"{s['base_url'].rstrip('/')}/chat/completions", json=body, timeout=s["timeout_s"],
                                  headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                if r.status_code == 401:
                    raise LLMError("OpenAI rejected the key (401). Check OPENAI_API_KEY in .env.")
                if r.status_code == 429:
                    last = LLMError("OpenAI rate limit or no credit left (429). Check your OpenAI billing page.")
                    time.sleep(2 * (attempt + 1))
                    continue
                r.raise_for_status()
                data = r.json()
                usage = data.get("usage") or {}
                self.calls += 1
                self.tokens_in += usage.get("prompt_tokens", 0)
                self.tokens_out += usage.get("completion_tokens", 0)
                return json.loads(data["choices"][0]["message"]["content"])
            except LLMError:
                raise
            except (requests.RequestException, KeyError, json.JSONDecodeError) as error:
                last = LLMError(f"OpenAI call failed: {type(error).__name__}: {error}")
                time.sleep(1.5 * (attempt + 1))
        raise last
