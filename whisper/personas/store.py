from __future__ import annotations

import json
import logging
from pathlib import Path

from whisper.personas.schema import Persona, PersonaExample

logger = logging.getLogger(__name__)

DEFAULT_PERSONAS: dict[str, dict] = {
    "work": {
        "id": "work",
        "display_name": "Work",
        "system_prompt": "Professional, concise, US English. No emojis unless asked.",
        "style_notes": ["Prefer clear structure", "Avoid slang"],
        "examples": [],
    },
    "student": {
        "id": "student",
        "display_name": "Student",
        "system_prompt": "Clear academic tone. Explain when helpful but stay concise.",
        "style_notes": ["Use proper terminology", "Neutral voice"],
        "examples": [],
    },
    "casual": {
        "id": "casual",
        "display_name": "Casual",
        "system_prompt": "Friendly, relaxed tone. Natural conversational English.",
        "style_notes": ["Short sentences OK", "Light humor when appropriate"],
        "examples": [],
    },
    "default": {
        "id": "default",
        "display_name": "Default",
        "system_prompt": "Clear, natural English. Preserve the speaker's intent.",
        "style_notes": [],
        "examples": [],
    },
}


class PersonaStore:
    def __init__(self, personas_dir: Path) -> None:
        self.personas_dir = personas_dir
        self.personas_dir.mkdir(parents=True, exist_ok=True)
        self._personas: dict[str, Persona] = {}
        self._load_all()

    def _load_all(self) -> None:
        self._personas.clear()
        for pid, template in DEFAULT_PERSONAS.items():
            path = self.personas_dir / f"{pid}.json"
            if not path.exists():
                path.write_text(json.dumps(template, indent=2), encoding="utf-8")
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._personas[pid] = Persona.from_dict(data)
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("Failed to load persona %s: %s", pid, exc)
                self._personas[pid] = Persona.from_dict(template)

    def list_ids(self) -> list[str]:
        order = ["work", "student", "casual", "default"]
        ids = list(self._personas.keys())
        return sorted(ids, key=lambda x: order.index(x) if x in order else 99)

    def get(self, persona_id: str) -> Persona:
        if persona_id not in self._personas:
            return self._personas.get("default", list(self._personas.values())[0])
        return self._personas[persona_id]

    def save(self, persona: Persona) -> None:
        path = self.personas_dir / f"{persona.id}.json"
        path.write_text(json.dumps(persona.to_dict(), indent=2), encoding="utf-8")
        self._personas[persona.id] = persona

    def add_example(self, persona_id: str, example: PersonaExample) -> None:
        persona = self.get(persona_id)
        persona.examples.append(example)
        if len(persona.examples) > 20:
            persona.examples = persona.examples[-20:]
        self.save(persona)

    def add_style_note(self, persona_id: str, note: str) -> None:
        persona = self.get(persona_id)
        if note and note not in persona.style_notes:
            persona.style_notes.append(note)
            if len(persona.style_notes) > 15:
                persona.style_notes = persona.style_notes[-15:]
            self.save(persona)

    def cycle_next(self, current_id: str) -> str:
        ids = self.list_ids()
        if current_id not in ids:
            return ids[0]
        idx = ids.index(current_id)
        return ids[(idx + 1) % len(ids)]
