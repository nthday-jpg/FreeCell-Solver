from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

SETTINGS_FILE = Path(".freecell_gui_settings.json")


@dataclass(slots=True)
class GuiSettings:
    music_volume: float = 0.35
    sfx_volume: float = 0.55
    music_muted: bool = False
    sfx_muted: bool = False
    max_expansions: int = 30000
    preferred_solver: str = "UCS"


def load_settings(path: Path = SETTINGS_FILE) -> GuiSettings:
    if not path.exists():
        return GuiSettings()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return GuiSettings()

    defaults = GuiSettings()
    return GuiSettings(
        music_volume=float(data.get("music_volume", defaults.music_volume)),
        sfx_volume=float(data.get("sfx_volume", defaults.sfx_volume)),
        music_muted=bool(data.get("music_muted", defaults.music_muted)),
        sfx_muted=bool(data.get("sfx_muted", defaults.sfx_muted)),
        max_expansions=int(data.get("max_expansions", defaults.max_expansions)),
        preferred_solver=str(data.get("preferred_solver", defaults.preferred_solver)),
    )


def save_settings(settings: GuiSettings, path: Path = SETTINGS_FILE) -> None:
    payload = asdict(settings)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
