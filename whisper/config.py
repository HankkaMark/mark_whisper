from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

WHISPER_HOME = Path(os.environ.get("WHISPER_HOME", Path.home() / ".whisper"))


DEFAULT_CONFIG: dict[str, Any] = {
    "providers": {"stt": "openai", "llm": "openai"},
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
        "stt_model": "whisper-1",
        "llm_model": "gpt-4o-mini",
    },
    "anthropic": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "model": "claude-sonnet-4-20250514",
    },
    "hotkeys": {
        "voice_key": "f8",
        "voice_action": "f8",
        "dictate": "f8",
        "edit_selection": "ctrl+shift+e",
        "cycle_persona": "ctrl+shift+p",
        "remember_style": "ctrl+shift+r",
    },
    "behavior": {
        "activation": "hold",
        "polish_dictation": True,
        "save_audio": False,
        "language": None,
        "clipboard_restore_delay_ms": 150,
    },
    "security": {
        "corporate_safe_mode": True,
        "global_hotkeys": False,
        "voice_hotkey_enabled": True,
        "synthetic_keystrokes": False,
        "tray_only_controls": True,
        "lazy_api_clients": True,
        "open_config_in_explorer": False,
    },
    "active_persona": "work",
}


# Single keys only — avoids conflicts with Ctrl+C, Ctrl+V, etc.
VOICE_KEYS = [
    "f8",
    "f9",
    "f10",
    "f11",
    "f12",
    "scroll lock",
    "pause",
    "insert",
    "home",
    "end",
    "page up",
    "page down",
    "`",
]

DEFAULT_VOICE_KEY = "f8"


def normalize_voice_key(key: str) -> str:
    return key.strip().lower()


def migrate_voice_key(hotkeys_raw: dict[str, Any]) -> str:
    key = hotkeys_raw.get("voice_key")
    if key:
        k = normalize_voice_key(str(key))
        if "+" not in k:
            return k
    action = hotkeys_raw.get("voice_action") or hotkeys_raw.get("dictate", "")
    if action and "+" not in str(action):
        return normalize_voice_key(str(action))
    return DEFAULT_VOICE_KEY


@dataclass
class HotkeyConfig:
    voice_key: str = DEFAULT_VOICE_KEY
    voice_action: str = DEFAULT_VOICE_KEY
    dictate: str = DEFAULT_VOICE_KEY
    edit_selection: str = "ctrl+shift+e"
    cycle_persona: str = "ctrl+shift+p"
    remember_style: str = "ctrl+shift+r"


@dataclass
class BehaviorConfig:
    activation: str = "hold"
    polish_dictation: bool = True
    save_audio: bool = False
    language: str | None = None
    clipboard_restore_delay_ms: int = 150


@dataclass
class SecurityConfig:
    """Settings that avoid keyloggers, synthetic input, and startup side-effects."""

    corporate_safe_mode: bool = True
    global_hotkeys: bool = False
    voice_hotkey_enabled: bool = True
    synthetic_keystrokes: bool = False
    tray_only_controls: bool = True
    lazy_api_clients: bool = True
    open_config_in_explorer: bool = False

    @property
    def use_hotkeys(self) -> bool:
        if self.voice_hotkey_enabled:
            return True
        if self.corporate_safe_mode:
            return False
        return self.global_hotkeys

    @property
    def use_synthetic_keys(self) -> bool:
        if self.corporate_safe_mode:
            return False
        return self.synthetic_keystrokes


@dataclass
class AppConfig:
    config_path: Path
    data_dir: Path
    providers_stt: str = "openai"
    providers_llm: str = "openai"
    openai_api_key: str = ""
    openai_base_url: str | None = None
    openai_stt_model: str = "whisper-1"
    openai_llm_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    active_persona: str = "work"

    @property
    def personas_dir(self) -> Path:
        return self.data_dir / "personas"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def ensure_default_config(config_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        config_path.write_text(
            yaml.dump(DEFAULT_CONFIG, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        logger.info("Created default config at %s", config_path)


def load_config(config_path: Path | None = None) -> AppConfig:
    data_dir = WHISPER_HOME
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "personas").mkdir(exist_ok=True)
    (data_dir / "logs").mkdir(exist_ok=True)

    cfg_path = config_path or (data_dir / "config.yaml")
    ensure_default_config(cfg_path)

    env_path = data_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    load_dotenv()

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    merged = _deep_merge(DEFAULT_CONFIG, raw)

    openai_cfg = merged.get("openai", {})
    anthropic_cfg = merged.get("anthropic", {})
    hotkeys_raw = merged.get("hotkeys", {})
    behavior_raw = merged.get("behavior", {})
    security_raw = merged.get("security", {})
    corp_safe = security_raw.get("corporate_safe_mode", True)

    return AppConfig(
        config_path=cfg_path,
        data_dir=data_dir,
        providers_stt=merged.get("providers", {}).get("stt", "openai"),
        providers_llm=merged.get("providers", {}).get("llm", "openai"),
        openai_api_key=os.environ.get(openai_cfg.get("api_key_env", "OPENAI_API_KEY"), ""),
        openai_base_url=os.environ.get(openai_cfg.get("base_url_env", "OPENAI_BASE_URL"))
        or openai_cfg.get("base_url"),
        openai_stt_model=openai_cfg.get("stt_model", "whisper-1"),
        openai_llm_model=openai_cfg.get("llm_model", "gpt-4o-mini"),
        anthropic_api_key=os.environ.get(
            anthropic_cfg.get("api_key_env", "ANTHROPIC_API_KEY"), ""
        ),
        anthropic_model=anthropic_cfg.get("model", "claude-sonnet-4-20250514"),
        hotkeys=_load_hotkey_config(hotkeys_raw),
        behavior=BehaviorConfig(
            activation=behavior_raw.get("activation", "hold"),
            polish_dictation=behavior_raw.get("polish_dictation", True),
            save_audio=behavior_raw.get("save_audio", False),
            language=behavior_raw.get("language"),
            clipboard_restore_delay_ms=behavior_raw.get(
                "clipboard_restore_delay_ms", 150
            ),
        ),
        security=SecurityConfig(
            corporate_safe_mode=corp_safe,
            global_hotkeys=security_raw.get("global_hotkeys", not corp_safe),
            voice_hotkey_enabled=security_raw.get("voice_hotkey_enabled", True),
            synthetic_keystrokes=security_raw.get(
                "synthetic_keystrokes", not corp_safe
            ),
            tray_only_controls=security_raw.get("tray_only_controls", corp_safe),
            lazy_api_clients=security_raw.get("lazy_api_clients", corp_safe),
            open_config_in_explorer=security_raw.get(
                "open_config_in_explorer", not corp_safe
            ),
        ),
        active_persona=merged.get("active_persona", "work"),
    )


def _load_hotkey_config(hotkeys_raw: dict[str, Any]) -> HotkeyConfig:
    voice_key = migrate_voice_key(hotkeys_raw)
    return HotkeyConfig(
        voice_key=voice_key,
        voice_action=voice_key,
        dictate=hotkeys_raw.get("dictate", voice_key),
        edit_selection=hotkeys_raw.get("edit_selection", "ctrl+shift+e"),
        cycle_persona=hotkeys_raw.get("cycle_persona", "ctrl+shift+p"),
        remember_style=hotkeys_raw.get("remember_style", "ctrl+shift+r"),
    )


def _read_config_raw(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _write_config_raw(config_path: Path, raw: dict[str, Any]) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.dump(raw, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def save_voice_key(config: AppConfig, key: str) -> HotkeyConfig:
    voice_key = normalize_voice_key(key)
    raw = _read_config_raw(config.config_path)
    hotkeys = raw.setdefault("hotkeys", {})
    hotkeys.pop("voice_modifier", None)
    hotkeys["voice_key"] = voice_key
    hotkeys["voice_action"] = voice_key
    hotkeys["dictate"] = voice_key
    _write_config_raw(config.config_path, raw)
    return _load_hotkey_config(hotkeys)


def save_api_credentials(
    data_dir: Path,
    api_key: str,
    base_url: str,
) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    env_path = data_dir / ".env"
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    values = {
        "OPENAI_API_KEY": api_key.strip(),
        "OPENAI_BASE_URL": base_url.strip(),
    }
    seen: set[str] = set()
    updated: list[str] = []
    for line in lines:
        key_part = line.split("=", 1)[0].strip() if "=" in line else ""
        if key_part in values:
            updated.append(f"{key_part}={values[key_part]}")
            seen.add(key_part)
        else:
            updated.append(line)
    for key_name, value in values.items():
        if key_name not in seen:
            updated.append(f"{key_name}={value}")
    env_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    load_dotenv(env_path, override=True)


def save_active_persona(config: AppConfig, persona_id: str) -> None:
    config.active_persona = persona_id
    raw = yaml.safe_load(config.config_path.read_text(encoding="utf-8")) or {}
    raw["active_persona"] = persona_id
    config.config_path.write_text(
        yaml.dump(raw, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
