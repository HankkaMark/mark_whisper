from __future__ import annotations

from openai import OpenAI

from whisper.personas.schema import Persona


class OpenAILLMAdapter:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ) -> None:
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model

    def _chat(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,
        )
        return (response.choices[0].message.content or "").strip()

    def polish_dictation(self, text: str, persona: Persona) -> str:
        system = (
            f"{persona.build_system_context()}\n\n"
            "You clean up dictated speech into written text. "
            "Preserve meaning and facts. Apply the persona tone. "
            "Return only the final text with no quotes or explanation."
        )
        user = f"Clean up this dictated text:\n\n{text}"
        return self._chat(system, user)

    def edit_text(self, original: str, instruction: str, persona: Persona) -> str:
        system = (
            f"{persona.build_system_context()}\n\n"
            "You rewrite text according to the user's instruction. "
            "Return only the rewritten text with no quotes or explanation."
        )
        user = f"Instruction: {instruction}\n\nOriginal:\n{original}"
        return self._chat(system, user)

    def generate_from_instruction(self, instruction: str, persona: Persona) -> str:
        system = (
            f"{persona.build_system_context()}\n\n"
            "You turn spoken instructions into ready-to-use text "
            "(emails, messages, notes, drafts). "
            "Apply the persona tone. "
            "Return only the final text with no quotes or explanation."
        )
        user = f"Instruction: {instruction}"
        return self._chat(system, user)

    def summarize_style_note(self, note: str, persona: Persona) -> str:
        system = (
            "Compress the user's preference into one short style note (one sentence). "
            "Return only the note."
        )
        user = f"Persona: {persona.display_name}\nPreference to remember: {note}"
        return self._chat(system, user)
