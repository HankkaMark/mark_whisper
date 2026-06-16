from __future__ import annotations

from anthropic import Anthropic

from whisper.personas.schema import Persona


class AnthropicLLMAdapter:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def _message(self, system: str, user: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=0.4,
        )
        parts = []
        for block in response.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts).strip()

    def polish_dictation(self, text: str, persona: Persona) -> str:
        system = (
            f"{persona.build_system_context()}\n\n"
            "You clean up dictated speech into written text. "
            "Preserve meaning and facts. Apply the persona tone. "
            "Return only the final text with no quotes or explanation."
        )
        user = f"Clean up this dictated text:\n\n{text}"
        return self._message(system, user)

    def edit_text(self, original: str, instruction: str, persona: Persona) -> str:
        system = (
            f"{persona.build_system_context()}\n\n"
            "You rewrite text according to the user's instruction. "
            "Return only the rewritten text with no quotes or explanation."
        )
        user = f"Instruction: {instruction}\n\nOriginal:\n{original}"
        return self._message(system, user)

    def generate_from_instruction(self, instruction: str, persona: Persona) -> str:
        system = (
            f"{persona.build_system_context()}\n\n"
            "You turn spoken instructions into ready-to-use text "
            "(emails, messages, notes, drafts). "
            "Apply the persona tone. "
            "Return only the final text with no quotes or explanation."
        )
        user = f"Instruction: {instruction}"
        return self._message(system, user)

    def summarize_style_note(self, note: str, persona: Persona) -> str:
        system = (
            "Compress the user's preference into one short style note (one sentence). "
            "Return only the note."
        )
        user = f"Persona: {persona.display_name}\nPreference to remember: {note}"
        return self._message(system, user)
