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
    }


def load():
    data = default()
    try:
        stored = json.loads(PATH.read_text())
    except (OSError, ValueError):
        return data
    if not isinstance(stored, dict):
        return data
    for k in ("coins", "best", "stage", "vehicle", "sound", "music", "driver", "horn", "name", "last_host"):
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


def save(data):
    try:
        PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        os.replace(tmp, PATH)
    except OSError:
        pass
