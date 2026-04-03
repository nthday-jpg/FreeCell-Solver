from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

SETTINGS_FILE = Path(".freecell_gui_settings.json")


@dataclass(slots=True)
class GuiSettings:
    music_volume: int = 35
    sfx_volume: int = 55
    music_muted: bool = False
    sfx_muted: bool = False
    preferred_solver: str = "UCS"
    external_audio_dir: str = ""


def load_settings(path: Path = SETTINGS_FILE) -> GuiSettings:
    if not path.exists():
        return GuiSettings()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return GuiSettings()

    defaults = GuiSettings()
    music_volume_raw = data.get("music_volume", defaults.music_volume)
    sfx_volume_raw = data.get("sfx_volume", defaults.sfx_volume)

    # Backward compatibility: old settings used 0.0..1.0 floats.
    if isinstance(music_volume_raw, (float, int)) and 0.0 <= float(music_volume_raw) <= 1.0:
        music_volume = int(round(float(music_volume_raw) * 100))
    else:
        music_volume = int(float(music_volume_raw))

    if isinstance(sfx_volume_raw, (float, int)) and 0.0 <= float(sfx_volume_raw) <= 1.0:
        sfx_volume = int(round(float(sfx_volume_raw) * 100))
    else:
        sfx_volume = int(float(sfx_volume_raw))

    return GuiSettings(
        music_volume=max(0, min(100, music_volume)),
        sfx_volume=max(0, min(100, sfx_volume)),
        music_muted=bool(data.get("music_muted", defaults.music_muted)),
        sfx_muted=bool(data.get("sfx_muted", defaults.sfx_muted)),
        preferred_solver=str(data.get("preferred_solver", defaults.preferred_solver)),
        external_audio_dir=str(data.get("external_audio_dir", defaults.external_audio_dir)),
    )


def save_settings(settings: GuiSettings, path: Path = SETTINGS_FILE) -> None:
    payload = asdict(settings)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
