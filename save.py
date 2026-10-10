"""Persistent progress: coins, per-vehicle upgrades, best distances, settings."""
import json
import os
from pathlib import Path

from config import STAGES, UPGRADES, VEHICLES

PATH = Path.home() / ".hill_rider" / "save.json"


def _fresh_levels():
    return {v["key"]: {u["key"]: 1 for u in UPGRADES} for v in VEHICLES}


def default():
    return {
        "coins": 0,
        "levels": _fresh_levels(),
        "best": {},
        "stage": STAGES[0]["key"],
        "vehicle": VEHICLES[0]["key"],
        "sound": True,
        "music": True,
        "driver": "default",
        "horn": "puppy",
        "name": "",
        "last_host": "",
        "player_id": "",
        "friends": {},
        "volume": {"master": 1.0, "music": 0.8, "sfx": 1.0, "voice": 1.0},
        "music_track": "auto",
        "graphics": "high",
        "fullscreen": False,
        "stats": {},
        "achievements": [],
        "trophies": {},
        "daily_done": "",
        "ghosts": True,
        "lang": "en",
        "story": {},                     # story mode progress, filled in by story.state()
    }


def _ensure_id(data):
    pid = str(data.get("player_id", ""))
    if not (pid.isdigit() and len(pid) == 6):
        import secrets
        data["player_id"] = str(secrets.randbelow(900000) + 100000)
        save(data)
    data["friends"] = {k: str(v) for k, v in data.get("friends", {}).items() if str(k).isdigit() and len(str(k)) == 6}
    return data


def load():
    data = _load()
    return _ensure_id(data)


def _load():
    from config import WEB
    data = default()
    try:
        if WEB:
            store = _web_storage()
            raw = store.getItem("hill_rider_save") if store is not None else None
            stored = json.loads(raw) if raw else {}
            if not raw:
                data["graphics"] = "low"
        else:
            stored = json.loads(PATH.read_text())
    except (OSError, ValueError, TypeError):
        return data
    if not isinstance(stored, dict):
        return data
    for k in ("coins", "best", "stage", "vehicle", "sound", "music", "driver", "horn", "name", "last_host",
              "player_id", "friends", "volume", "music_track", "graphics", "fullscreen", "stats", "achievements",
              "trophies", "daily_done", "ghosts", "lang", "story"):
        if k in stored and type(stored[k]) is type(data[k]):
            data[k] = stored[k]
    levels = stored.get("levels", {})
    if isinstance(levels, dict):
        if "engine" in levels:                    # old save: one set of upgrades for the jeep
            levels = {"jeep": levels}
        for vkey, lv in levels.items():
            if vkey in data["levels"] and isinstance(lv, dict):
                for ukey, value in lv.items():
                    if ukey in data["levels"][vkey]:
                        data["levels"][vkey][ukey] = max(1, int(value))
    if data["stage"] not in {s["key"] for s in STAGES}:
        data["stage"] = STAGES[0]["key"]
    if data["vehicle"] not in {v["key"] for v in VEHICLES}:
        data["vehicle"] = VEHICLES[0]["key"]
    from drivers import DRIVER_BY_KEY
    if data["driver"] not in DRIVER_BY_KEY:
        data["driver"] = "default"
    if data["horn"] not in ("puppy", "ship"):
        data["horn"] = "puppy"
    return data


def _web_storage():
    try:
        import platform as browser       # pygbag replaces `platform` with the browser bridge
        return browser.window.localStorage
    except (ImportError, AttributeError):
        return None


def save(data):
    from config import WEB
    if WEB:
        store = _web_storage()
        if store is not None:
            store.setItem("hill_rider_save", json.dumps(data))
        return
    try:
        PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        os.replace(tmp, PATH)
    except OSError:
        pass
