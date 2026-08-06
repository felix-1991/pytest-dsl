"""Directory hook filename recognition and ordering."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


HookKind = Literal["setup", "teardown"]

_HOOK_FILE_RE = re.compile(
    r"^(?P<kind>setup|teardown)"
    r"(?:_(?:"
    r"(?P<order>\d+)(?:_(?P<ordered_label>.+))?"
    r"|(?P<named_label>(?!\d+(?:_|$)).+)"
    r"))?"
    r"\.(?P<extension>dsl|auto)$"
)


@dataclass(frozen=True)
class HookFile:
    """Parsed directory hook metadata."""

    path: Path
    kind: HookKind
    order: int | None
    label: str | None
    extension: str

    @property
    def legacy(self) -> bool:
        """Whether this is the unnumbered legacy hook filename."""
        return self.order is None and self.label is None


def parse_hook_file(path: str | Path) -> HookFile | None:
    """Parse a supported hook filename, returning ``None`` for normal cases."""
    candidate = Path(path)
    match = _HOOK_FILE_RE.fullmatch(candidate.name)
    if match is None:
        return None

    order_text = match.group("order")
    label = match.group("ordered_label") or match.group("named_label")
    return HookFile(
        path=candidate,
        kind=match.group("kind"),
        order=int(order_text) if order_text is not None else None,
        label=label,
        extension=match.group("extension"),
    )


def is_hook_file(path: str | Path) -> bool:
    """Return whether a path follows the directory hook naming convention."""
    return parse_hook_file(path) is not None


def discover_hook_files(directory: str | Path, kind: HookKind) -> list[Path]:
    """Discover hook files in their execution order for one directory.

    Legacy ``setup.dsl`` runs first. Named hooks without an explicit order use
    order zero, while numbered hooks run by ascending numeric order and
    filename. Teardown uses the exact reverse order so cleanup follows stack
    semantics.

    When the same stem exists as both ``.dsl`` and ``.auto``, the ``.dsl`` file
    wins for compatibility with native pytest-dsl collection.
    """
    root = Path(directory)
    if not root.exists() or not root.is_dir():
        return []

    hooks_by_stem: dict[str, HookFile] = {}
    for candidate in root.iterdir():
        if not candidate.is_file():
            continue
        hook = parse_hook_file(candidate)
        if hook is None or hook.kind != kind:
            continue

        existing = hooks_by_stem.get(candidate.stem)
        if existing is None or (existing.extension == "auto" and hook.extension == "dsl"):
            hooks_by_stem[candidate.stem] = hook

    hooks = sorted(hooks_by_stem.values(), key=_hook_sort_key)
    if kind == "teardown":
        hooks.reverse()
    return [hook.path for hook in hooks]


def _hook_sort_key(hook: HookFile) -> tuple[int, int, str, str]:
    if hook.legacy:
        return (0, 0, "", hook.path.name)
    return (1, hook.order or 0, hook.path.stem.casefold(), hook.path.name)
