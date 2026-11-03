#!/usr/bin/env python3
"""
Shared YAML helpers for the Home Assistant scripts.

Home Assistant YAML is not plain YAML: it uses custom tags (!include, !secret,
!input, !env_var, !include_dir_*) and ESPHome adds more (!lambda, !extend...).
`yaml.safe_load` rejects all of them, so every real configuration.yaml looks
"broken" to a naive validator. This module gives every script the same loader.

- Tags are kept as `HATag` objects (a str subclass with `.tag`), so scripts can
  tell `!secret wifi` apart from the literal string "wifi".
- Duplicate keys are recorded (Home Assistant warns about them and the last one
  silently wins, which is a classic source of "my automation vanished").
- Line numbers are kept for mappings in `loader.marks` when needed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator, List, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - reported by callers
    yaml = None  # type: ignore


HA_TAGS = (
    "include",
    "include_dir_list",
    "include_dir_named",
    "include_dir_merge_list",
    "include_dir_merge_named",
    "secret",
    "input",
    "env_var",
)

# Folders inside /config that never hold user YAML worth validating.
SKIP_DIRS = {
    ".storage", ".cloud", ".git", ".github", ".vscode", ".venv", "venv",
    "custom_components", "www", "node_modules", "deps", "tts", "backups",
    "image", "media", "__pycache__", ".esphome", "zigbee2mqtt",
}


class HATag(str):
    """A scalar that came from a custom tag, e.g. `!secret api_key`."""

    tag: str = ""

    def __new__(cls, value: str, tag: str):
        obj = super().__new__(cls, value)
        obj.tag = tag
        return obj

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"!{self.tag} {str.__str__(self)}"


class HATaggedList(list):
    tag: str = ""


class HATaggedDict(dict):
    tag: str = ""


class LineDict(dict):
    """A mapping that remembers the 1-based line where it starts."""

    line: int = 0


if yaml is not None:

    class HALoader(yaml.SafeLoader):
        """SafeLoader that understands Home Assistant / ESPHome tags."""

        def __init__(self, stream):
            super().__init__(stream)
            self.duplicate_keys: List[Tuple[str, int]] = []

        def construct_mapping(self, node, deep=False):  # noqa: D401
            seen = {}
            for key_node, _ in node.value:
                try:
                    key = self.construct_object(key_node, deep=True)
                except Exception:  # unhashable / odd keys: let base raise
                    continue
                try:
                    hash(key)
                except TypeError:
                    continue
                if key in seen and key != "<<":
                    self.duplicate_keys.append((str(key), key_node.start_mark.line + 1))
                seen[key] = True
            return super().construct_mapping(node, deep=deep)

    def _construct_tag(loader, tag_suffix, node):
        tag = tag_suffix.lstrip("!")
        if isinstance(node, yaml.ScalarNode):
            return HATag(loader.construct_scalar(node), tag)
        if isinstance(node, yaml.SequenceNode):
            out = HATaggedList(loader.construct_sequence(node, deep=True))
            out.tag = tag
            return out
        if isinstance(node, yaml.MappingNode):
            out = HATaggedDict(loader.construct_mapping(node, deep=True))
            out.tag = tag
            return out
        return None

    def _construct_line_map(loader, node):
        data = LineDict()
        data.line = node.start_mark.line + 1
        yield data
        data.update(loader.construct_mapping(node))

    HALoader.add_constructor("tag:yaml.org,2002:map", _construct_line_map)

    for _tag in HA_TAGS:
        HALoader.add_constructor(
            f"!{_tag}", lambda loader, node, t=_tag: _construct_tag(loader, t, node)
        )
    # Any other tag (ESPHome !lambda, !extend, !remove, custom ones): keep it.
    HALoader.add_multi_constructor("!", _construct_tag)


def require_yaml() -> Optional[str]:
    """Return an error message when PyYAML is missing, else None."""
    if yaml is None:
        return "PyYAML not installed. Run: pip install pyyaml (Alpine: apk add py3-yaml)"
    return None


def load_text(text: str) -> Tuple[Any, List[Tuple[str, int]]]:
    """Parse HA YAML text. Returns (data, duplicate_keys). Raises yaml.YAMLError."""
    loader = HALoader(text)
    try:
        data = loader.get_single_data()
    finally:
        loader.dispose()
    return data, loader.duplicate_keys


def load_file(path: Path) -> Tuple[Any, List[Tuple[str, int]]]:
    return load_text(Path(path).read_text(encoding="utf-8"))


def iter_yaml_files(root: Path) -> Iterator[Path]:
    """Yield YAML files under `root`, skipping folders that never hold config."""
    root = Path(root)
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        )
        for name in sorted(filenames):
            if name.endswith((".yaml", ".yml")) and not name.startswith("."):
                yield Path(dirpath) / name


def line_of(node: Any) -> int:
    return getattr(node, "line", 0)


def walk(data: Any, path: str = "") -> Iterator[Tuple[str, Any]]:
    """Yield (path, node) for every dict in a nested structure."""
    if isinstance(data, dict):
        yield path, data
        for key, value in data.items():
            child = f"{path}.{key}" if path else str(key)
            yield from walk(value, child)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            yield from walk(item, f"{path}[{i}]")
