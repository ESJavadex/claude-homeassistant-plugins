#!/usr/bin/env python3
"""
Home Assistant Configuration Checker

Analyzes HA configuration files for structure, dependencies, and best practices.
Usage: python3 check_config.py <directory_or_file> [--verbose] [--include-unloaded]

- `!include` / `!secret` are read from the parsed YAML, so commented-out lines
  never count.
- `!secret` is resolved like Home Assistant does: secrets.yaml next to the file,
  then each parent folder up to the config folder (ESPHome files use
  esphome/secrets.yaml).
- In a config folder, files that configuration.yaml never loads (archive and
  draft folders) are skipped and counted; --include-unloaded checks them too.
"""

import sys
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ha_yaml import (  # noqa: E402
    ensure_yaml, find_config_root, is_unloaded, iter_tags, iter_yaml_files,
    load_text, loaded_files, require_yaml, secrets_files_for,
)

ensure_yaml()
if require_yaml():
    print(json.dumps({"error": require_yaml()}))
    sys.exit(1)


class HAConfigChecker:
    """Analyzes Home Assistant configuration structure and dependencies."""

    HA_DOMAINS = {
        "automation", "script", "scene", "group", "input_boolean",
        "input_number", "input_text", "input_select", "input_datetime",
        "input_button", "counter", "timer", "schedule", "template",
        "sensor", "binary_sensor", "switch", "light", "cover", "fan",
        "climate", "media_player", "camera", "notify", "tts", "mqtt",
        "rest", "command_line", "shell_command", "homeassistant",
        "frontend", "lovelace", "logger", "recorder", "history",
        "logbook", "person", "zone", "device_tracker", "geo_location"
    }

    def __init__(self, verbose: bool = False, include_unloaded: bool = False):
        self.verbose = verbose
        self.include_unloaded = include_unloaded
        self.not_loaded: List[str] = []
        self.files_checked: List[str] = []
        self.entities_found: Dict[str, Set[str]] = {}
        self.secrets_used: Set[str] = set()
        self.includes_found: List[dict] = []
        self.issues: List[dict] = []
        self.suggestions: List[str] = []
        self.secret_refs: List[tuple] = []  # (name, file)
        self.automation_ids: Dict[str, str] = {}
        self.config_root: Optional[Path] = None

    def check_path(self, path: str) -> dict:
        """Check a file or directory."""
        p = Path(path)

        if not p.exists():
            return {"error": f"Path not found: {path}"}

        if p.is_file():
            return self._check_single_file(p)
        elif p.is_dir():
            return self._check_directory(p)

        return {"error": f"Invalid path: {path}"}

    def _rel(self, path) -> str:
        """Path relative to the config folder, so two automations.yaml are never confused."""
        try:
            return str(Path(path).resolve().relative_to(self.config_root.resolve()))
        except (ValueError, AttributeError):
            return str(path)

    def _check_directory(self, directory: Path) -> dict:
        """Check all YAML files in a directory (skips .storage, custom_components, www...)."""
        self.config_root = find_config_root(directory) or directory
        loaded = None if self.include_unloaded else loaded_files(self.config_root)
        yaml_files = []
        for f in iter_yaml_files(directory):
            if is_unloaded(f, self.config_root, loaded):
                self.not_loaded.append(self._rel(f))
            else:
                yaml_files.append(f)

        if not yaml_files:
            return {"error": f"No YAML files found in {directory}"}

        # Check for main configuration file
        main_config = directory / "configuration.yaml"
        has_main_config = main_config.exists()

        for yaml_file in yaml_files:
            self._analyze_file(yaml_file)

        self._check_secrets_defined()
        return self._generate_report(directory, has_main_config)

    def _check_single_file(self, file_path: Path) -> dict:
        """Check a single YAML file."""
        self.config_root = find_config_root(file_path) or file_path.parent
        self._analyze_file(file_path)
        self._check_secrets_defined()
        return self._generate_report(file_path.parent, (file_path.parent / "configuration.yaml").exists())

    def _secret_names(self, secrets_file: Path) -> Optional[Set[str]]:
        """Key names only; values are never read out or reported."""
        cache = self.__dict__.setdefault("_secret_cache", {})
        if secrets_file not in cache:
            try:
                data, _ = load_text(secrets_file.read_text(encoding="utf-8"))
                cache[secrets_file] = set(map(str, data.keys())) if isinstance(data, dict) else set()
            except Exception:
                cache[secrets_file] = None
        return cache[secrets_file]

    def _check_secrets_defined(self) -> None:
        """Report !secret names that no reachable secrets.yaml defines."""
        reported = set()
        for name, where in self.secret_refs:
            files = secrets_files_for(Path(where), self.config_root)
            if not files:
                key = ("nofile", where)
                if key not in reported:
                    reported.add(key)
                    self.issues.append({
                        "file": self._rel(where),
                        "type": "missing_secrets_file",
                        "message": "uses !secret but there is no secrets.yaml next to it or in a parent folder",
                    })
                continue
            names = [self._secret_names(f) for f in files]
            if any(n is None for n in names):
                continue  # unreadable secrets.yaml: do not guess
            if not any(name in n for n in names) and (name, where) not in reported:
                reported.add((name, where))
                self.issues.append({
                    "file": self._rel(where),
                    "type": "undefined_secret",
                    "message": f"!secret {name} is not defined in {', '.join(self._rel(f) for f in files)}",
                })

    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single YAML file."""
        self.files_checked.append(str(file_path))

        if file_path.name == "secrets.yaml":
            return  # never parse or report secret values
        try:
            content = file_path.read_text(encoding='utf-8')
            data, duplicates = load_text(content)
        except PermissionError as e:
            self.issues.append({"file": str(file_path), "type": "read_error", "message": str(e)})
            return
        except Exception as e:
            if type(e).__name__.endswith("Error") and "yaml" in type(e).__module__:
                self.issues.append({
                    "file": str(file_path),
                    "type": "syntax_error",
                    "message": str(e)
                })
                return
            self.issues.append({
                "file": str(file_path),
                "type": "read_error",
                "message": str(e)
            })
            return

        for key, line in duplicates:
            self.issues.append({
                "file": str(file_path),
                "type": "duplicate_key",
                "message": f"Line {line}: duplicate key '{key}' (only the last one is used)",
            })

        if not data:
            return

        # automations.yaml / scripts.yaml style files (no top-level domain key)
        if isinstance(data, list) and file_path.name.startswith("automation"):
            self._check_automations(data, file_path)
        if isinstance(data, dict) and file_path.name.startswith("script") and all(
            isinstance(v, dict) and "sequence" in v for v in data.values()
        ):
            self._check_scripts(data, file_path)

        # !include and !secret, from the parsed data (comments never count)
        self._find_includes(data, file_path)
        self._find_secrets(data, file_path)

        # Analyze structure
        if isinstance(data, dict):
            self._analyze_structure(data, file_path)

    def _find_includes(self, data, file_path: Path) -> None:
        """Find !include directives."""
        for tag in iter_tags(data):
            include_type = tag.tag
            if not include_type.startswith("include"):
                continue
            target = str(tag).strip()
            self.includes_found.append({
                "file": str(file_path),
                "type": include_type,
                "target": target
            })
            resolved = (file_path.parent / target)
            if not resolved.exists() and include_type != "include":
                self.suggestions.append(
                    f"{self._rel(file_path)}: !{include_type} {target} points to a folder that does not exist (HA treats it as empty)"
                )
            elif not resolved.exists():
                self.issues.append({
                    "file": self._rel(file_path),
                    "type": "missing_include",
                    "message": f"!{include_type} {target}: not found (relative to {file_path.parent.name or '.'}/)",
                })

    def _find_secrets(self, data, file_path: Path) -> None:
        """Find !secret references."""
        for tag in iter_tags(data):
            if tag.tag == "secret":
                name = str(tag).strip()
                self.secrets_used.add(name)
                self.secret_refs.append((name, str(file_path)))

    def _analyze_structure(self, data: dict, file_path: Path) -> None:
        """Analyze configuration structure."""
        for key, value in data.items():
            # Track known domains
            if key in self.HA_DOMAINS:
                if key not in self.entities_found:
                    self.entities_found[key] = set()

                # Extract entity IDs
                self._extract_entities(value, key)

            # Check for automation structure
            if key == "automation":
                self._check_automations(value, file_path)

            # Check for script structure
            if key == "script":
                self._check_scripts(value, file_path)

    def _extract_entities(self, value, domain: str) -> None:
        """Extract entity identifiers from configuration."""
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    # Check for alias or id
                    entity_id = item.get("id") or item.get("alias") or item.get("name")
                    if entity_id:
                        self.entities_found[domain].add(str(entity_id))
        elif isinstance(value, dict):
            for entity_name in value.keys():
                self.entities_found[domain].add(entity_name)

    def _check_automations(self, automations, file_path: Path) -> None:
        """Check automation configurations."""
        if not isinstance(automations, list):
            return

        for i, automation in enumerate(automations):
            if not isinstance(automation, dict):
                continue

            # Check for missing alias
            if "alias" not in automation and "use_blueprint" not in automation:
                self.suggestions.append(
                    f"Automation #{i+1} in {file_path.name} has no 'alias'"
                )

            # Duplicate ids break the UI editor and traces
            aid = automation.get("id")
            if aid is not None:
                where = f"{self._rel(file_path)} (automation #{i+1})"
                if str(aid) in self.automation_ids:
                    self.issues.append({
                        "file": self._rel(file_path),
                        "type": "duplicate_automation_id",
                        "message": f"Automation id '{aid}' is also used in {self.automation_ids[str(aid)]}",
                    })
                else:
                    self.automation_ids[str(aid)] = where

            # Check for missing id
            if "id" not in automation:
                self.suggestions.append(
                    f"Automation '{automation.get('alias', f'#{i+1}')}' in {file_path.name}: "
                    "Consider adding 'id' for UI editing support"
                )

            # Check for mode (good practice)
            if "mode" not in automation and self.verbose:
                self.suggestions.append(
                    f"Automation '{automation.get('alias', f'#{i+1}')}': "
                    "Consider specifying 'mode' (single/restart/queued/parallel)"
                )

    def _check_scripts(self, scripts, file_path: Path) -> None:
        """Check script configurations."""
        if not isinstance(scripts, dict):
            return

        for script_id, script in scripts.items():
            if not isinstance(script, dict):
                continue

            # Check for missing alias
            if "alias" not in script:
                self.suggestions.append(
                    f"Script '{script_id}' in {file_path.name}: Consider adding 'alias'"
                )

    def _generate_report(self, base_path: Path, has_main_config: bool) -> dict:
        """Generate the analysis report."""
        report = {
            "path": str(base_path),
            "files_checked": len(self.files_checked),
            "has_configuration_yaml": has_main_config,
            "summary": {
                "domains_found": list(self.entities_found.keys()),
                "total_entities": sum(len(v) for v in self.entities_found.values()),
                "secrets_referenced": len(self.secrets_used),
                "includes_found": len(self.includes_found),
                "issues_found": len(self.issues)
            },
            "not_loaded": {
                "count": len(self.not_loaded),
                "files": self.not_loaded[:20],
                "note": "Not loaded by configuration.yaml, so skipped. Use --include-unloaded to check them too.",
            } if self.not_loaded else None,
            "issues": self.issues if self.issues else None,
            "suggestions": self.suggestions if self.suggestions else None
        }

        if self.verbose:
            report["details"] = {
                "files": self.files_checked,
                "entities": {k: list(v) for k, v in self.entities_found.items()},
                "secrets": list(self.secrets_used),
                "includes": self.includes_found
            }

        # Add overall status
        if self.issues:
            report["status"] = "issues_found"
        elif self.suggestions:
            report["status"] = "ok_with_suggestions"
        else:
            report["status"] = "ok"

        return report


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: check_config.py <directory_or_file> [--verbose]",
            "examples": [
                "python3 check_config.py /config",
                "python3 check_config.py configuration.yaml --verbose"
            ]
        }, indent=2))
        sys.exit(1)

    path = sys.argv[1]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    checker = HAConfigChecker(verbose=verbose, include_unloaded="--include-unloaded" in sys.argv)
    result = checker.check_path(path)

    print(json.dumps(result, indent=2))

    # Exit code based on issues
    if result.get("issues"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
