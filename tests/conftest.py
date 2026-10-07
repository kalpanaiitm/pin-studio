import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FIX = ROOT / "tests" / "fixtures"

from pinstudio.config import load_settings  # noqa: E402
from pinstudio.fetch import parse_html  # noqa: E402


@pytest.fixture
def settings():
    s = load_settings()
    s["llm"]["mode"] = "mock"
    return s


@pytest.fixture
def page():
    return parse_html((FIX / "vinted_post.html").read_text(encoding="utf-8"), "https://moneysavvyuk.com/how-to-sell-on-vinted-uk/")


@pytest.fixture
def product():
    return parse_html((FIX / "payhip_product.html").read_text(encoding="utf-8"), "https://payhip.com/b/l09hx")


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status_code, self._payload = status, payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


@pytest.fixture
def fake_openai(monkeypatch):
    """Replies in OpenAI's chat-completions format with prepared content; records the requests."""
    data = json.loads((FIX / "fake_openai.json").read_text(encoding="utf-8"))
    calls = []

    def post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "body": json, "headers": headers})
        system = json["messages"][0]["content"]
        content = data["keywords"] if "Pinterest SEO specialist" in system else data["pins"]
        import json as j
        return FakeResponse({"choices": [{"message": {"content": j.dumps(content)}}],
                             "usage": {"prompt_tokens": 3000, "completion_tokens": 1500}})

    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.setattr("pinstudio.llm.requests.post", post)
    return calls
