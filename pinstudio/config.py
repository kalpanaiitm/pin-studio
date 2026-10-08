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


PREFS = ROOT / "data" / "preferences.json"


def load_prefs() -> dict:
    import json
    try:
        return json.loads(PREFS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_prefs(**values):
    import json
    prefs = {**load_prefs(), **values}
    PREFS.parent.mkdir(parents=True, exist_ok=True)
    PREFS.write_text(json.dumps(prefs, indent=1), encoding="utf-8")


def load_settings(path: Path = None, use_prefs: bool = True) -> dict:
    s = yaml.safe_load((path or ROOT / "settings.yaml").read_text(encoding="utf-8"))
    if use_prefs and path is None:
        prefs = load_prefs()
        if "pins_per_day" in prefs:
            s["schedule"]["pins_per_day"] = int(prefs["pins_per_day"])
    s["llm"]["mode"] = os.getenv("LLM_MODE", s["llm"]["mode"])
    s["llm"]["model"] = os.getenv("OPENAI_MODEL", s["llm"]["model"])
    return s


def paths(root: Path = None) -> dict:
    root = Path(root or ROOT)
    p = {"root": root, "data": root / "data", "output": root / "output", "history": root / "data" / "history.csv"}
    for key in ("data", "output"):
        p[key].mkdir(parents=True, exist_ok=True)
    return p
