from __future__ import annotations

import logging
from dataclasses import dataclass, field

from whisper.config import AppConfig

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticResult:
    category: str
    ok: bool
    summary: str
    fix: str = ""

    def tray_line(self) -> str:
        icon = "OK" if self.ok else "!!"
        return f"[{icon}] {self.category}: {self.summary}"


@dataclass
class ErrorReport:
    category: str
    summary: str
    fix: str = ""
    detail: str = ""


def format_exception(exc: Exception) -> ErrorReport:
    text = str(exc).lower()
    name = type(exc).__name__

    if name in ("PermissionDeniedError", "AuthenticationError") or "401" in text:
        if "expired" in text:
            return ErrorReport(
                "API",
                "API token expired",
                "Open Settings and paste a fresh Gateway token.",
                str(exc),
            )
        return ErrorReport(
            "API",
            "API authentication failed",
            "Check API key in Settings.",
            str(exc),
        )

    if name == "RateLimitError" or "429" in text:
        return ErrorReport(
            "API",
            "API rate limit reached",
            "Wait a moment and try again.",
            str(exc),
        )

    if name in ("APIConnectionError", "ConnectError", "ConnectionError") or "connect" in text:
        return ErrorReport(
            "API",
            "Cannot reach API (network/firewall)",
            "Check VPN, proxy, or Gateway URL in Settings.",
            str(exc),
        )

    if name == "APITimeoutError" or "timeout" in text:
        return ErrorReport(
            "API",
            "API request timed out",
            "Retry or check network connection.",
            str(exc),
        )

    if "whisper" in text or "transcri" in text or "audio" in text:
        return ErrorReport(
            "API",
            "Speech-to-text failed",
            "Gateway may not support whisper-1. Check logs or ask IT.",
            str(exc),
        )

    if name in ("PortAudioError", "OSError") or "audio" in text or "microphone" in text:
        return ErrorReport(
            "Audio",
            "Microphone error",
            "Allow mic access for Python in Windows Settings → Privacy.",
            str(exc),
        )

    if "clipboard" in text:
        return ErrorReport(
            "Clipboard",
            "Clipboard access failed",
            "Copy text manually (Ctrl+C) and retry.",
            str(exc),
        )

    return ErrorReport("App", f"Unexpected error: {name}", "See whisper.log for details.", str(exc))


def check_config(config: AppConfig) -> DiagnosticResult:
    if not config.openai_api_key or config.openai_api_key.startswith("sk-your"):
        return DiagnosticResult(
            "Config",
            False,
            "API key missing",
            "Settings → paste your Gateway token.",
        )
    if not config.openai_base_url:
        return DiagnosticResult(
            "Config",
            False,
            "Gateway URL missing",
            "Settings → paste the Gateway URL.",
        )
    return DiagnosticResult("Config", True, "API key and URL configured")


def check_api(config: AppConfig) -> DiagnosticResult:
    cfg = check_config(config)
    if not cfg.ok:
        return DiagnosticResult("API", False, cfg.summary, cfg.fix)

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
            timeout=15.0,
        )
        client.chat.completions.create(
            model=config.openai_llm_model,
            messages=[{"role": "user", "content": "ping"}],
        )
        return DiagnosticResult("API", True, f"Gateway OK ({config.openai_llm_model})")
    except Exception as exc:
        report = format_exception(exc)
        return DiagnosticResult("API", False, report.summary, report.fix)


def check_audio() -> DiagnosticResult:
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        inputs = [d for d in devices if d.get("max_input_channels", 0) > 0]
        if not inputs:
            return DiagnosticResult(
                "Audio",
                False,
                "No microphone found",
                "Plug in a mic or enable one in Windows Sound settings.",
            )
        default = sd.query_devices(kind="input")
        name = default.get("name", "unknown")
        return DiagnosticResult("Audio", True, f"Microphone: {name[:40]}")
    except Exception as exc:
        report = format_exception(exc)
        return DiagnosticResult("Audio", False, report.summary, report.fix)


def check_hotkey(
    *,
    listening: bool,
    registered: bool,
    hotkey: str,
    error: str | None = None,
    hooks_enabled: bool,
) -> DiagnosticResult:
    if not listening:
        return DiagnosticResult(
            "Hotkey",
            False,
            "Listening is OFF",
            "Tray → Start listening.",
        )
    if not hooks_enabled:
        return DiagnosticResult(
            "Hotkey",
            False,
            "Hotkeys disabled in config",
            "Set voice_hotkey_enabled: true in config.yaml.",
        )
    if error:
        return DiagnosticResult(
            "Hotkey",
            False,
            f"Cannot register '{hotkey}'",
            error,
        )
    if not registered:
        return DiagnosticResult(
            "Hotkey",
            False,
            f"'{hotkey}' not active",
            "IT may block keyboard hooks. Use tray Manual actions, or run as Administrator.",
        )
    return DiagnosticResult("Hotkey", True, f"Hold {hotkey} to record")


def probe_hotkey_library(hotkey: str) -> tuple[bool, str]:
    try:
        import keyboard

        def _test() -> None:
            pass

        key = hotkey.strip().lower()
        if "+" in key:
            keyboard.add_hotkey(key, _test, suppress=False)
            keyboard.remove_hotkey(key)
        else:
            hook = keyboard.on_press_key(key, _test, suppress=False)
            keyboard.unhook(hook)
        return True, ""
    except ImportError:
        return False, "keyboard library not installed."
    except Exception as exc:
        msg = str(exc)
        if "administrator" in msg.lower() or "access" in msg.lower():
            return False, "Blocked by Windows — try Run as Administrator, or use tray menu."
        return False, f"Security software may block global hotkeys. ({msg[:120]})"


def run_all_checks(
    config: AppConfig,
    *,
    listening: bool,
    hotkey_registered: bool,
    hotkey_error: str | None,
    hooks_enabled: bool,
    skip_api: bool = False,
) -> list[DiagnosticResult]:
    results = [
        check_config(config),
        check_audio(),
        check_hotkey(
            listening=listening,
            registered=hotkey_registered,
            hotkey=config.hotkeys.voice_key,
            error=hotkey_error,
            hooks_enabled=hooks_enabled,
        ),
    ]
    if not skip_api:
        results.insert(1, check_api(config))
    return results


def summarize(results: list[DiagnosticResult]) -> str:
    failed = [r for r in results if not r.ok]
    if not failed:
        return "All checks passed"
    return failed[0].summary


@dataclass
class StatusBoard:
    """Tracks latest user-visible status and errors for the tray."""

    status: str = "Starting..."
    last_error: ErrorReport | None = None
    diagnostics: list[DiagnosticResult] = field(default_factory=list)

    def set_status(self, message: str) -> None:
        self.status = message

    def set_error(self, report: ErrorReport) -> None:
        self.last_error = report
        self.status = f"[{report.category}] {report.summary}"

    def clear_error(self) -> None:
        self.last_error = None

    def error_line(self) -> str | None:
        if not self.last_error:
            return None
        return f"Error [{self.last_error.category}]: {self.last_error.summary}"

    def fix_line(self) -> str | None:
        if not self.last_error or not self.last_error.fix:
            return None
        return f"Fix: {self.last_error.fix}"
