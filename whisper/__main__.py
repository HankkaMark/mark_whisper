from __future__ import annotations

import sys


def main() -> None:
    try:
        from whisper.app import WhisperApp

        app = WhisperApp()
        app.run()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:
        print(f"Whisper failed to start: {exc}", file=sys.stderr)
        print(
            "Ensure API keys are set (OPENAI_API_KEY, ANTHROPIC_API_KEY) "
            f"in %USERPROFILE%\\.whisper\\.env or system environment.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
