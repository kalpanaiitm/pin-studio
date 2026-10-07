import os
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[1]
if load_dotenv:
    load_dotenv(ROOT / ".env")


def load_settings(path: Path = None) -> dict:
    s = yaml.safe_load((path or ROOT / "settings.yaml").read_text(encoding="utf-8"))
    s["llm"]["mode"] = os.getenv("LLM_MODE", s["llm"]["mode"])
    s["llm"]["model"] = os.getenv("OPENAI_MODEL", s["llm"]["model"])
    return s


def paths(root: Path = None) -> dict:
    root = Path(root or ROOT)
    p = {"root": root, "data": root / "data", "output": root / "output", "history": root / "data" / "history.csv"}
    for key in ("data", "output"):
        p[key].mkdir(parents=True, exist_ok=True)
    return p
