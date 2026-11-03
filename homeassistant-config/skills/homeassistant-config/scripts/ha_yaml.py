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
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator, List, Optional, Set, Tuple

# Newest Home Assistant release whose changes these rules know about.
RULES_CURRENT_TO = "2026.11"

# Interpreters to try when the current one has no PyYAML (for example a venv
# made without --system-site-packages, like the add-on's persistent packages).
PYTHON_FALLBACKS = ("/usr/bin/python3", "/usr/local/bin/python3", "/bin/python3", "/usr/bin/python")

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

        def flatten_mapping(self, node):
            # `<<: !include common.yaml` (ESPHome packages, some HA configs): the
            # merged file is not loaded here, so drop that merge instead of failing.
            node.value = [
                (k, v) for k, v in node.value
                if not (k.tag == "tag:yaml.org,2002:merge" and v.tag.startswith("!"))
            ]
            return super().flatten_mapping(node)

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
        return (f"PyYAML is not available to {sys.executable} and no other Python with it was found. "
                "Run: pip install pyyaml (Alpine: apk add py3-yaml)")
    return None


def ensure_yaml() -> None:
    """Re-run this script with a Python that has PyYAML, if this one lacks it.

    Call it first thing in main(), before reading stdin. If no interpreter has
    PyYAML it returns and the caller reports `require_yaml()`.
    """
    if yaml is not None or os.environ.get("HA_PLUGIN_REEXEC"):
        return
    # Do not skip a candidate because it is the same binary: a venv's python3
    # is a symlink to /usr/bin/python3, which sees PyYAML once run outside it.
    # HA_PLUGIN_REEXEC stops any loop.
    candidates = [os.environ.get("HA_PLUGIN_PYTHON", "")] + list(PYTHON_FALLBACKS)
    for cand in candidates:
        if not cand or not os.path.isfile(cand) or os.path.abspath(cand) == os.path.abspath(sys.executable or ""):
            continue
        try:
            ok = subprocess.run([cand, "-c", "import yaml"], capture_output=True, timeout=10).returncode == 0
        except Exception:
            ok = False
        if ok:
            os.environ["HA_PLUGIN_REEXEC"] = "1"
            try:
                os.execv(cand, [cand] + sys.argv)
            except OSError:
                return


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


# ---------------------------------------------------------------- versions

def parse_version(value: Any) -> Optional[Tuple[int, int]]:
    """'2026.10.4', '2026.11.0b2', '2026.11.0.dev2026...' -> (2026, 10)."""
    m = re.match(r"\s*(\d{4})\.(\d{1,2})", str(value or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def find_config_root(path: Path, levels: int = 8) -> Optional[Path]:
    """The nearest folder at or above `path` that holds configuration.yaml."""
    p = Path(path).resolve()
    if p.is_file():
        p = p.parent
    for _ in range(levels):
        if (p / "configuration.yaml").is_file():
            return p
        if p.parent == p:
            break
        p = p.parent
    return None


def installed_version(path: Path) -> Optional[str]:
    """The Home Assistant version that runs this config, if we can tell.

    `HA_VERSION` in the environment wins; otherwise `.HA_VERSION`, which Home
    Assistant writes in the config folder on every start.
    """
    env = os.environ.get("HA_VERSION", "").strip()
    if env:
        return env if parse_version(env) else None
    root = find_config_root(path)
    if root is None:
        return None
    try:
        text = (root / ".HA_VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text if parse_version(text) else None


# ------------------------------------------------------------ loaded files

def resolve_include(base: Path, target: str, root: Optional[Path]) -> Path:
    """Where `!include target` in `base` points.

    Relative paths are relative to the including file. Absolute `/config/...`
    or `/homeassistant/...` paths are mapped onto the config folder when it is
    mounted somewhere else (add-ons, a git checkout).
    """
    t = str(target).strip()
    p = Path(t)
    if not p.is_absolute():
        return Path(base).parent / p
    if p.exists() or root is None:
        return p
    for prefix in ("/config/", "/homeassistant/"):
        if t.startswith(prefix):
            return Path(root) / t[len(prefix):]
    return p


def iter_tags(data: Any) -> Iterator[HATag]:
    """Every tagged scalar (`!include x`, `!secret y`...) in parsed data. Comments never get here."""
    if isinstance(data, HATag):
        yield data
    elif isinstance(data, HATaggedList) and data and isinstance(data[0], str):
        yield HATag(data[0], data.tag)  # lovelace_gen: !include [file.yaml, {vars}]
    elif isinstance(data, dict):
        for value in data.values():
            yield from iter_tags(value)
    elif isinstance(data, list):
        for item in data:
            yield from iter_tags(item)


def loaded_files(root: Path) -> Optional[Set[Path]]:
    """Files Home Assistant actually loads, following configuration.yaml.

    Follows `!include` and `!include_dir_*` (recursive, `*.yaml` like HA) from
    configuration.yaml, plus YAML dashboards declared under `lovelace:`.
    Returns None when there is no configuration.yaml to start from.
    """
    root = Path(root).resolve()
    main = root / "configuration.yaml"
    if not main.is_file() or yaml is None:
        return None
    seen: Set[Path] = set()
    stack = [main]
    if (root / "ui-lovelace.yaml").is_file():
        stack.append(root / "ui-lovelace.yaml")
    while stack:
        f = Path(stack.pop()).resolve()
        if f in seen or not f.is_file():
            continue
        seen.add(f)
        try:
            data, _ = load_file(f)
        except Exception:
            continue
        for tag in iter_tags(data):
            if tag.tag == "include":
                stack.append(resolve_include(f, tag, root))
            elif tag.tag.startswith("include_dir_"):
                d = resolve_include(f, tag, root)
                if d.is_dir():
                    stack.extend(sorted(p for p in d.rglob("*.yaml") if not p.name.startswith(".")))
        lovelace = data.get("lovelace") if isinstance(data, dict) else None
        if not isinstance(lovelace, dict) and isinstance(data, dict):
            lovelace = data  # `lovelace: !include lovelace.yaml`
        dashboards = lovelace.get("dashboards") if isinstance(lovelace, dict) else None
        if isinstance(dashboards, dict):
            for dash in dashboards.values():
                if isinstance(dash, dict) and isinstance(dash.get("filename"), str):
                    stack.append(root / dash["filename"])
    return seen


# Folders whose YAML is loaded by something other than configuration.yaml.
LOADED_ELSEWHERE = {"blueprints", "esphome"}


def is_unloaded(path: Path, root: Path, loaded: Optional[Set[Path]]) -> bool:
    """True when `path` sits in the config folder but nothing loads it."""
    if loaded is None:
        return False
    p = Path(path).resolve()
    if p in loaded or p.name == "secrets.yaml":
        return False
    try:
        rel = p.relative_to(Path(root).resolve())
    except ValueError:
        return False
    return not (set(part.lower() for part in rel.parts[:-1]) & LOADED_ELSEWHERE)


def secrets_files_for(path: Path, root: Optional[Path]) -> List[Path]:
    """secrets.yaml files that can resolve `!secret` in `path`, nearest first.

    Home Assistant looks next to the file and then in each parent folder up to
    the config folder; ESPHome uses the secrets.yaml next to the node file.
    """
    out: List[Path] = []
    p = Path(path).resolve().parent
    stop = Path(root).resolve() if root else None
    for _ in range(10):
        if (p / "secrets.yaml").is_file():
            out.append(p / "secrets.yaml")
        if stop is None or p == stop or p.parent == p:
            break
        p = p.parent
    return out


# Keys whose values are credentials. A YAML error quotes the offending line
# (ESPHome nodes keep Wi-Fi and API passwords in plain text), and that output
# ends up in the Claude session, so their values are masked.
SECRET_KEY = re.compile(
    r"""(?ix)
    ^(?P<key>\s*(?:-\s+)?["']?(?:key|[\w.-]*(?:password|passwd|pwd|passphrase|secret|token|api_?key|apikey
        |access_key|private_key|encryption_key|psk|credentials?|auth)[\w.-]*)["']?\s*[:=]\s*)
    (?P<value>(?!!secret\b|!env_var\b)\S.*?)\s*$""",
    re.M,
)
URL_CREDENTIALS = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://[^\s:/@]+:)[^\s@/]+@")


def redact(text: str) -> str:
    """Mask credential values in text that quotes YAML (error messages, snippets)."""
    if not text:
        return text
    text = SECRET_KEY.sub(lambda m: m.group("key") + "***", text)
    return URL_CREDENTIALS.sub(r"\1***@", text)
