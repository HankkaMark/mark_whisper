from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PersonaExample:
    instruction: str
    before: str
    after: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PersonaExample:
        return cls(
            instruction=data.get("instruction", ""),
            before=data.get("before", ""),
            after=data.get("after", ""),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "instruction": self.instruction,
            "before": self.before,
            "after": self.after,
        }


@dataclass
class Persona:
    id: str
    display_name: str
    system_prompt: str
    style_notes: list[str] = field(default_factory=list)
    examples: list[PersonaExample] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Persona:
        return cls(
            id=data["id"],
            display_name=data.get("display_name", data["id"]),
            system_prompt=data.get("system_prompt", ""),
            style_notes=list(data.get("style_notes", [])),
            examples=[PersonaExample.from_dict(e) for e in data.get("examples", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "system_prompt": self.system_prompt,
            "style_notes": self.style_notes,
            "examples": [e.to_dict() for e in self.examples],
        }

    def build_system_context(self) -> str:
        parts = [self.system_prompt]
        if self.style_notes:
            parts.append("Style notes:\n" + "\n".join(f"- {n}" for n in self.style_notes))
        if self.examples:
            shots = []
            for ex in self.examples[-5:]:
                shots.append(
                    f"Example ({ex.instruction}):\nBefore: {ex.before}\nAfter: {ex.after}"
                )
            parts.append("Examples of preferred style:\n" + "\n\n".join(shots))
        return "\n\n".join(parts)
