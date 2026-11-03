#!/usr/bin/env python3
"""
Home Assistant Duplicate Finder

Finds duplicate and similar automations/scripts in HA configuration.
Usage: python3 find_duplicates.py <directory_or_file> [--verbose]
"""

import sys
import os
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from difflib import SequenceMatcher
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ha_yaml import (  # noqa: E402
    ensure_yaml, find_config_root, is_unloaded, iter_yaml_files, load_text, loaded_files, redact, require_yaml,
)

ensure_yaml()
if require_yaml():
    print(json.dumps({"error": require_yaml()}))
    sys.exit(1)


TEMPLATE_ENTITY_KEYS = {
    "sensor", "binary_sensor", "button", "number", "select", "image", "weather",
    "switch", "light", "cover", "fan", "lock", "vacuum", "alarm_control_panel", "event", "update",
}


def canonical(obj):
    """Rewrite old keys to current ones so old and new syntax compare equal.

    platform -> trigger (trigger items), service -> action (steps),
    data_template -> data, trigger/condition/action lists -> plural keys.
    """
    if isinstance(obj, list):
        return [canonical(x) for x in obj]
    if not isinstance(obj, dict):
        return obj
    out = {}
    for key, value in obj.items():
        new_key = key
        if key == "platform" and "trigger" not in obj:
            new_key = "trigger"
        elif key == "service" and "action" not in obj and isinstance(value, str):
            new_key = "action"
        elif key == "data_template" and "data" not in obj:
            new_key = "data"
        elif key in ("trigger", "condition", "action") and isinstance(value, list) and key + "s" not in obj:
            new_key = key + "s"
        out[new_key] = canonical(value)
    return out


class DuplicateFinder:
    """Finds duplicate and similar automations/scripts in HA configuration."""

    SIMILARITY_THRESHOLD = 0.8  # 80% similarity for "similar" items

    def __init__(self, verbose: bool = False, include_unloaded: bool = False):
        self.verbose = verbose
        self.include_unloaded = include_unloaded
        self.not_loaded: List[str] = []
        self.automations: List[dict] = []
        self.scripts: List[dict] = []
        self.files_checked: List[str] = []
        self.errors: List[dict] = []

    def scan_path(self, path: str) -> dict:
        """Scan a file or directory for duplicates."""
        p = Path(path)

        if not p.exists():
            return {"error": f"Path not found: {path}"}

        if p.is_file():
            self._scan_file(p)
        elif p.is_dir():
            self._scan_directory(p)

        return self._analyze_duplicates()

    def _scan_directory(self, directory: Path) -> None:
        """Scan all YAML files in a directory."""
        root = find_config_root(directory)
        loaded = loaded_files(root) if root and not self.include_unloaded else None
        for yaml_file in iter_yaml_files(directory):
            # Copies in archive/draft folders are not loaded by HA: not duplicates
            if root and is_unloaded(yaml_file, root, loaded):
                self.not_loaded.append(str(yaml_file))
                continue
            self._scan_file(yaml_file)

    def _scan_file(self, file_path: Path) -> None:
        """Scan a single YAML file."""
        self.files_checked.append(str(file_path))

        try:
            content = file_path.read_text(encoding='utf-8')
            data, _ = load_text(content)
        except Exception as e:
            self.errors.append({
                "file": str(file_path),
                "error": f"YAML parse error: {redact(str(e))}"
            })
            return

        if not data:
            return

        # Handle different file structures
        if isinstance(data, dict):
            # File with domain keys (e.g., configuration.yaml with automation: key)
            if "automation" in data:
                self._extract_automations(data["automation"], file_path)
            if "script" in data:
                self._extract_scripts(data["script"], file_path)
            # scripts.yaml: {script_id: {sequence: [...]}}
            if "script" not in data and data and all(
                isinstance(v, dict) and "sequence" in v for v in data.values()
            ):
                self._extract_scripts(data, file_path)
        elif isinstance(data, list):
            # File is a list of automations (e.g., automations.yaml)
            if file_path.stem in ("automations", "automation"):
                self._extract_automations(data, file_path)
            elif file_path.stem in ("scripts", "script"):
                self._extract_scripts_from_list(data, file_path)
            else:
                # Try to detect type from content
                if data and isinstance(data[0], dict):
                    if "trigger" in data[0] or "triggers" in data[0]:
                        self._extract_automations(data, file_path)

    def _extract_automations(self, automations, file_path: Path) -> None:
        """Extract automations from configuration."""
        if not isinstance(automations, list):
            return

        for idx, automation in enumerate(automations):
            if not isinstance(automation, dict):
                continue
            if TEMPLATE_ENTITY_KEYS & set(map(str, automation)):
                continue  # trigger-based template entity (template: - triggers: ... sensor: ...)

            auto_info = {
                "file": str(file_path),
                "index": idx,
                "alias": automation.get("alias", f"Unnamed #{idx+1}"),
                "id": automation.get("id"),
                "triggers": self._normalize_triggers(automation),
                "conditions": self._normalize_conditions(automation),
                "actions": self._normalize_actions(automation),
                "variables": canonical(automation.get("variables")),
                # blueprint automations have no triggers/actions of their own
                "use_blueprint": canonical(automation.get("use_blueprint")),
                "entities": self._extract_entity_ids(automation),
                "raw": automation
            }
            auto_info["hash"] = self._compute_hash(auto_info)
            self.automations.append(auto_info)

    def _extract_scripts(self, scripts, file_path: Path) -> None:
        """Extract scripts from dict configuration."""
        if not isinstance(scripts, dict):
            return

        for script_id, script in scripts.items():
            if not isinstance(script, dict):
                continue

            script_info = {
                "file": str(file_path),
                "script_id": script_id,
                "alias": script.get("alias", script_id),
                "sequence": self._normalize_sequence(script),
                "variables": canonical(script.get("variables")),
                "entities": self._extract_entity_ids(script),
                "raw": script
            }
            script_info["hash"] = self._compute_hash(script_info)
            self.scripts.append(script_info)

    def _extract_scripts_from_list(self, scripts, file_path: Path) -> None:
        """Extract scripts from list format."""
        if not isinstance(scripts, list):
            return

        for idx, script in enumerate(scripts):
            if not isinstance(script, dict):
                continue

            script_info = {
                "file": str(file_path),
                "index": idx,
                "alias": script.get("alias", f"Script #{idx+1}"),
                "sequence": self._normalize_sequence(script),
                "variables": canonical(script.get("variables")),
                "entities": self._extract_entity_ids(script),
                "raw": script
            }
            script_info["hash"] = self._compute_hash(script_info)
            self.scripts.append(script_info)

    def _normalize_triggers(self, automation: dict) -> List[dict]:
        """Normalize triggers for comparison."""
        triggers = automation.get("triggers") or automation.get("trigger") or []
        if isinstance(triggers, dict):
            triggers = [triggers]
        return self._sort_dict_list(canonical(triggers))

    def _normalize_conditions(self, automation: dict) -> List[dict]:
        """Normalize conditions for comparison."""
        conditions = automation.get("conditions") or automation.get("condition") or []
        if isinstance(conditions, dict):
            conditions = [conditions]
        return self._sort_dict_list(canonical(conditions))

    def _normalize_actions(self, automation: dict) -> List[dict]:
        """Normalize actions for comparison."""
        actions = automation.get("actions") or automation.get("action") or []
        if isinstance(actions, dict):
            actions = [actions]
        return canonical(actions)  # Preserve order for actions

    def _normalize_sequence(self, script: dict) -> List[dict]:
        """Normalize script sequence for comparison."""
        sequence = script.get("sequence") or []
        if isinstance(sequence, dict):
            sequence = [sequence]
        return canonical(sequence)

    def _sort_dict_list(self, items: List) -> List:
        """Sort a list of dicts for consistent comparison."""
        if not items:
            return []
        try:
            return sorted(items, key=lambda x: json.dumps(x, sort_keys=True) if isinstance(x, dict) else str(x))
        except TypeError:
            return items

    ENTITY_KEYS = ("entity_id", "entity", "entities")

    def _extract_entity_ids(self, config: dict) -> Set[str]:
        """Entity IDs referenced by a config (entity_id/entity/entities keys only).

        Action names such as light.turn_on or notify.mobile_app_x are NOT entities
        and are ignored, otherwise every automation that notifies the same phone
        looks "similar".
        """
        entities: Set[str] = set()

        def add(value):
            if isinstance(value, str):
                if re.match(r'^[a-z0-9_]+\.[a-z0-9_]+$', value):
                    entities.add(value)
            elif isinstance(value, list):
                for v in value:
                    add(v)
            elif isinstance(value, dict) and "entity" in value:
                add(value["entity"])

        def walk(value):
            if isinstance(value, list):
                for item in value:
                    walk(item)
            elif isinstance(value, dict):
                for k, v in value.items():
                    if k in self.ENTITY_KEYS:
                        add(v)
                    else:
                        walk(v)

        walk(config)
        return entities

    def _compute_hash(self, item: dict) -> str:
        """Compute a hash of the meaningful parts for exact duplicate detection."""
        # For automations, hash triggers + actions (ignore alias/id)
        if "triggers" in item:
            hashable = {
                "triggers": item["triggers"],
                "conditions": item["conditions"],
                "actions": item["actions"],
                "variables": item.get("variables"),
                "use_blueprint": item.get("use_blueprint"),
            }
        else:
            # For scripts (same sequence with different variables is not a duplicate)
            hashable = {
                "sequence": item["sequence"],
                "variables": item.get("variables"),
            }

        content = json.dumps(hashable, sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()

    def _analyze_duplicates(self) -> dict:
        """Analyze collected items for duplicates and similarities."""
        result = {
            "files_scanned": len(self.files_checked),
            "automations_found": len(self.automations),
            "scripts_found": len(self.scripts),
            "exact_duplicates": {
                "automations": [],
                "scripts": []
            },
            "similar_items": {
                "automations": [],
                "scripts": []
            },
            "trigger_conflicts": [],
            "errors": self.errors if self.errors else None
        }

        # Find exact duplicates (same hash)
        result["exact_duplicates"]["automations"] = self._find_exact_duplicates(self.automations, "automation")
        result["exact_duplicates"]["scripts"] = self._find_exact_duplicates(self.scripts, "script")

        # Find similar items
        result["similar_items"]["automations"] = self._find_similar_items(self.automations, "automation")
        result["similar_items"]["scripts"] = self._find_similar_items(self.scripts, "script")

        # Find trigger conflicts (multiple automations with same trigger)
        result["trigger_conflicts"] = self._find_trigger_conflicts()

        # Generate summary
        total_exact = (
            len(result["exact_duplicates"]["automations"]) +
            len(result["exact_duplicates"]["scripts"])
        )
        total_similar = (
            len(result["similar_items"]["automations"]) +
            len(result["similar_items"]["scripts"])
        )

        if total_exact == 0 and total_similar == 0 and not result["trigger_conflicts"]:
            result["status"] = "clean"
            result["message"] = "No duplicates or conflicts found"
        else:
            result["status"] = "duplicates_found"
            result["summary"] = {
                "exact_duplicate_groups": total_exact,
                "similar_item_groups": total_similar,
                "trigger_conflict_groups": len(result["trigger_conflicts"])
            }

        if self.verbose:
            result["details"] = {
                "files": self.files_checked,
                "all_automations": [
                    {"alias": a["alias"], "file": a["file"], "id": a.get("id")}
                    for a in self.automations
                ],
                "all_scripts": [
                    {"alias": s["alias"], "file": s["file"], "script_id": s.get("script_id")}
                    for s in self.scripts
                ]
            }

        return result

    def _find_exact_duplicates(self, items: List[dict], item_type: str) -> List[dict]:
        """Find items with identical hashes."""
        hash_groups = defaultdict(list)

        for item in items:
            hash_groups[item["hash"]].append(item)

        duplicates = []
        for hash_val, group in hash_groups.items():
            if len(group) > 1:
                duplicates.append({
                    "type": item_type,
                    "count": len(group),
                    "items": [
                        {
                            "alias": item["alias"],
                            "file": item["file"],
                            "id": item.get("id") or item.get("script_id"),
                            "index": item.get("index")
                        }
                        for item in group
                    ]
                })

        return duplicates

    def _find_similar_items(self, items: List[dict], item_type: str) -> List[dict]:
        """Group items that look alike. Pairs are merged into clusters, so ten
        near-identical scripts give one group of ten, not 45 pairs."""
        n = len(items)
        parent = list(range(n))
        best: Dict[int, float] = {}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i in range(n):
            for j in range(i + 1, n):
                if items[i]["hash"] == items[j]["hash"]:
                    continue  # exact duplicates are reported separately
                score = self._calculate_similarity(items[i], items[j])
                if score >= self.SIMILARITY_THRESHOLD:
                    ri, rj = find(i), find(j)
                    if ri != rj:
                        parent[rj] = ri
                    root = find(i)
                    best[root] = max(best.get(root, 0), best.pop(rj, 0) if rj != root else 0, score)

        clusters: Dict[int, List[int]] = {}
        for i in range(n):
            clusters.setdefault(find(i), []).append(i)

        groups = []
        for root, members in clusters.items():
            if len(members) < 2:
                continue
            first, second = items[members[0]], items[members[1]]
            groups.append({
                "type": item_type,
                "size": len(members),
                "similarity": f"{best.get(root, self.SIMILARITY_THRESHOLD):.0%}",
                "reason": self._get_similarity_reason(first, second),
                "items": [
                    {
                        "alias": items[m]["alias"],
                        "file": items[m]["file"],
                        "id": items[m].get("id") or items[m].get("script_id"),
                    }
                    for m in members
                ],
            })
        groups.sort(key=lambda g: -g["size"])
        return groups

    def _calculate_similarity(self, item1: dict, item2: dict) -> float:
        """Weighted similarity in [0, 1]: name 0.25, entities 0.35, logic 0.4."""
        parts = []
        parts.append((SequenceMatcher(None, item1["alias"].lower(), item2["alias"].lower()).ratio(), 0.25))

        entities1 = item1.get("entities", set())
        entities2 = item2.get("entities", set())
        if entities1 or entities2:
            overlap = len(entities1 & entities2) / max(len(entities1 | entities2), 1)
            parts.append((overlap, 0.35))

        bp1, bp2 = item1.get("use_blueprint"), item2.get("use_blueprint")
        if bp1 or bp2:
            # Blueprint automations: their logic is the blueprint plus its inputs.
            same_bp = isinstance(bp1, dict) and isinstance(bp2, dict) and bp1.get("path") == bp2.get("path")
            logic = self._compare_structures(bp1, bp2) if same_bp else 0.0
            parts.append((logic, 0.4))
        elif "triggers" in item1 and "triggers" in item2:
            logic = (self._compare_structures(item1["triggers"], item2["triggers"])
                     + self._compare_structures(item1.get("actions", []), item2.get("actions", []))) / 2
            parts.append((logic, 0.4))
        elif "sequence" in item1 and "sequence" in item2:
            parts.append((self._compare_structures(item1["sequence"], item2["sequence"]), 0.4))

        total_weight = sum(w for _, w in parts)
        return sum(s * w for s, w in parts) / total_weight if total_weight else 0.0

    def _compare_structures(self, struct1, struct2) -> float:
        """Compare two structures for similarity."""
        str1 = json.dumps(struct1, sort_keys=True, default=str)
        str2 = json.dumps(struct2, sort_keys=True, default=str)
        return SequenceMatcher(None, str1, str2).ratio()

    def _get_similarity_reason(self, item1: dict, item2: dict) -> str:
        """Get a human-readable reason for similarity."""
        reasons = []

        # Check name similarity
        name_sim = SequenceMatcher(
            None,
            item1["alias"].lower(),
            item2["alias"].lower()
        ).ratio()
        if name_sim > 0.7:
            reasons.append("similar names")

        # Check entity overlap
        entities1 = item1.get("entities", set())
        entities2 = item2.get("entities", set())
        if entities1 and entities2:
            common = entities1 & entities2
            if common:
                reasons.append(f"shared entities: {', '.join(list(common)[:3])}")

        # Check trigger similarity
        if "triggers" in item1 and "triggers" in item2:
            if self._compare_structures(item1["triggers"], item2["triggers"]) > 0.8:
                reasons.append("similar triggers")

        return "; ".join(reasons) if reasons else "structural similarity"

    def _find_trigger_conflicts(self) -> List[dict]:
        """Find automations with potentially conflicting triggers."""
        trigger_groups = defaultdict(list)

        for auto in self.automations:
            for trigger in auto.get("triggers", []):
                if isinstance(trigger, dict):
                    # Create a simplified trigger key
                    trigger_type = trigger.get("trigger") or trigger.get("platform", "unknown")
                    entity = trigger.get("entity_id", "")

                    if isinstance(entity, list):
                        entity = ",".join(sorted(entity))

                    key = f"{trigger_type}:{entity}"
                    if entity:  # Only track if there's an entity
                        trigger_groups[key].append(auto)

        conflicts = []
        for trigger_key, autos in trigger_groups.items():
            if len(autos) > 1:
                conflicts.append({
                    "trigger": trigger_key,
                    "count": len(autos),
                    "automations": [
                        {
                            "alias": a["alias"],
                            "file": a["file"],
                            "id": a.get("id")
                        }
                        for a in autos
                    ]
                })

        return conflicts


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: find_duplicates.py <directory_or_file> [--verbose]",
            "examples": [
                "python3 find_duplicates.py /config",
                "python3 find_duplicates.py automations.yaml --verbose"
            ]
        }, indent=2))
        sys.exit(1)

    path = sys.argv[1]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    finder = DuplicateFinder(verbose=verbose, include_unloaded="--include-unloaded" in sys.argv)
    result = finder.scan_path(path)
    if finder.not_loaded:
        result["not_loaded"] = {
            "count": len(finder.not_loaded),
            "files": finder.not_loaded[:20],
            "note": "Not loaded by configuration.yaml, so skipped. Use --include-unloaded to compare them too.",
        }

    print(json.dumps(result, indent=2, default=str))

    # Exit code based on findings
    # Only exit 1 for actual duplicates, not trigger conflicts (often intentional)
    exact_dupes = result.get("exact_duplicates", {})
    similar = result.get("similar_items", {})
    has_real_duplicates = (
        len(exact_dupes.get("automations", [])) > 0 or
        len(exact_dupes.get("scripts", [])) > 0 or
        len(similar.get("automations", [])) > 0 or
        len(similar.get("scripts", [])) > 0
    )
    if has_real_duplicates:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
