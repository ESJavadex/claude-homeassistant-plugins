#!/usr/bin/env python3
"""
Home Assistant dashboard (Lovelace) validator, updated for HA 2026.

Checks a dashboard for structural errors and for syntax that still works but
has been replaced (call-service, layout_options, section titles, ...).

Accepts:
- a YAML dashboard (`ui-lovelace.yaml`, any file under `dashboards:`), with
  `!include` / `!secret` tags,
- the UI storage file (`.storage/lovelace`, `.storage/lovelace.<id>`, JSON),
- a snippet: a single card (a mapping with `type:`), a list of cards, a single
  view (a mapping with `sections:`), or a `lovelace:` block from
  configuration.yaml.

Usage:
    python3 lovelace_validator.py <file> [--strict]

Output is JSON. `valid` is false when there are errors (or any warning with
--strict). Exit code 0 when valid, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ha_yaml import HATag, LineDict, ensure_yaml, line_of, load_text, require_yaml  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover - reported through require_yaml()
    yaml = None  # type: ignore


# --------------------------------------------------------------------------
# Known types (frontend 2026.11)
# --------------------------------------------------------------------------

BUILTIN_CARDS = {
    "alarm-panel", "alert", "area", "button", "calendar", "clock",
    "conditional", "date", "distribution", "entities", "entity",
    "entity-filter", "gauge", "glance", "grid", "heading", "history-graph",
    "horizontal-stack", "humidifier", "iframe", "light", "logbook", "map",
    "markdown", "media-control", "picture", "picture-elements",
    "picture-entity", "picture-glance", "plant-status", "sensor",
    "shopping-list", "shortcut", "statistic", "statistics-graph",
    "thermostat", "tile", "todo-list", "vertical-stack", "weather-forecast",
    # energy, power and water
    "energy-carbon-consumed-gauge", "energy-compare", "energy-date-selection",
    "energy-devices-detail-graph", "energy-devices-graph",
    "energy-distribution", "energy-gas-graph", "energy-grid-balance",
    "energy-grid-neutrality-gauge", "energy-sankey",
    "energy-self-sufficiency-gauge", "energy-solar-consumed-gauge",
    "energy-solar-graph", "energy-sources-table", "energy-usage-graph",
    "energy-water-graph", "power-sankey", "power-sources-graph",
    "water-sankey", "water-flow-sankey",
    # used by the built-in strategies; valid but rarely written by hand
    "home-summary", "repairs", "updates", "discovered-devices", "toggle-group",
    # legacy alias still registered
    "entity-button",
}

# Types people write that do not exist, with the right replacement.
MISNAMED_CARDS = {
    "webpage": "the card type is `iframe` (\"Webpage\" is the name of the dashboard and of the card in the UI)",
    "weather": "use `weather-forecast`",
    "statistics": "use `statistic` (one value) or `statistics-graph`",
    "section": "sections are not cards; put the cards in a `type: grid` section",
}

NESTED_CARDS_KEY = {"horizontal-stack", "vertical-stack", "grid"}

VIEW_TYPES = {"sections", "masonry", "panel", "sidebar"}

BADGE_TYPES = {
    "entity", "alert", "shortcut", "entity-filter", "state-label",
    "power-total", "gas-total", "water-total",
}

HEADING_BADGE_TYPES = {"entity", "button"}

PICTURE_ELEMENTS = {
    "state-badge", "state-icon", "state-label", "service-button",
    "action-button", "icon", "image", "conditional",
}

FEATURE_TYPES = {
    "alarm-modes", "area-controls", "bar-gauge", "button",
    "climate-fan-modes", "climate-hvac-modes", "climate-preset-modes",
    "climate-swing-horizontal-modes", "climate-swing-modes",
    "counter-actions", "cover-open-close", "cover-position",
    "cover-position-favorite", "cover-tilt", "cover-tilt-favorite",
    "cover-tilt-position", "date-set", "fan-direction", "fan-oscillate",
    "fan-preset-modes", "fan-speed", "humidifier-modes", "humidifier-toggle",
    "lawn-mower-commands", "light-brightness", "light-color",
    "light-color-favorites", "light-color-temp", "light-effect",
    "lock-commands", "lock-open-door", "media-player-playback",
    "media-player-sound-mode", "media-player-source",
    "media-player-volume-buttons", "media-player-volume-slider",
    "numeric-input", "precipitation-forecast", "select-options",
    "target-humidity", "target-temperature", "temperature-forecast",
    "timer-actions", "timer-presets", "toggle", "trend-graph",
    "update-actions", "vacuum-commands", "vacuum-fan-speed",
    "valve-open-close", "valve-position", "valve-position-favorite",
    "water-heater-operation-modes",
}

SECTION_STRATEGIES = {"common-controls", "device", "entities"}
VIEW_STRATEGIES = {
    "original-states", "energy", "energy-overview", "water", "gas", "power",
    "map", "iframe", "area", "areas-overview", "home-overview",
    "home-media-players", "home-area", "home-other-devices", "light",
    "security", "climate", "maintenance",
}
DASHBOARD_STRATEGIES = {"original-states", "map", "iframe", "areas", "home", "energy"}

ACTIONS = {
    "more-info", "toggle", "perform-action", "navigate", "url", "assist",
    "none", "fire-dom-event", "call-service",
}

ACTION_KEYS = {
    "tap_action", "hold_action", "double_tap_action",
    "icon_tap_action", "icon_hold_action", "icon_double_tap_action",
}

CONDITIONS_WITH_CHILDREN = {"and", "or", "not"}
CONDITIONS_WITH_ENTITY = {"state", "numeric_state"}

ENTITY_ID_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
TEMPLATE_MARKERS = ("{{", "{%", "[[[", "*")


def _is_dynamic(value: str) -> bool:
    """Values we cannot check: templates, JS templates, wildcards, tags."""
    return isinstance(value, HATag) or any(m in value for m in TEMPLATE_MARKERS)


REGISTRY_FILES = {"lovelace_dashboards", "lovelace_resources"}


class LovelaceValidator:
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.findings: List[Dict[str, Any]] = []
        self.card_types: Dict[str, int] = {}
        self.custom_cards: Set[str] = set()
        self.entities: Set[str] = set()
        self.views = 0
        self.sections = 0
        self._seen: Set[int] = set()
        self.skipped: Optional[str] = None
        self._warned_entities: Set[str] = set()

    # ------------------------------------------------------------------ util

    def add(self, level: str, node: Any, path: str, message: str,
            since: Optional[str] = None, line: Optional[int] = None) -> None:
        if line is None:
            line = line_of(node) or None
        self.findings.append({
            "level": level,
            "line": line,
            "path": path or "(root)",
            "message": message,
            "since": since,
        })

    def _once(self, node: Any) -> bool:
        """True the first time a given mapping is checked."""
        key = id(node)
        if key in self._seen:
            return False
        self._seen.add(key)
        return True

    # ----------------------------------------------------------------- entry

    def validate_file(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        fmt = "unknown"
        if not path.exists():
            self.add("error", None, "", f"File not found: {file_path}")
            return self._result(path, fmt)
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover
            self.add("error", None, "", f"Cannot read file: {exc}")
            return self._result(path, fmt)

        data = None
        if path.suffix == ".json" or path.name.startswith("lovelace") and not path.suffix:
            try:
                data = json.loads(text)
                fmt = "json"
            except json.JSONDecodeError:
                data = None
        if data is None and text.lstrip().startswith("{"):
            try:
                data = json.loads(text)
                fmt = "json"
            except json.JSONDecodeError:
                data = None

        if data is None:
            missing = require_yaml()
            if missing:
                self.add("error", None, "", missing)
                return self._result(path, fmt)
            try:
                data, duplicates = load_text(text)
                fmt = "yaml"
            except yaml.YAMLError as exc:
                mark = getattr(exc, "problem_mark", None)
                line = mark.line + 1 if mark else None
                self.add("error", None, "", f"YAML syntax error: {exc}", line=line)
                return self._result(path, "yaml")
            for key, line in duplicates:
                self.add("warning", None, key,
                         f"Duplicate key '{key}': only the last one is used", line=line)

        if fmt == "json" and isinstance(data, dict) and isinstance(data.get("data"), dict):
            if "config" in data["data"]:
                data = data["data"]["config"]
            elif "items" in data["data"] or path.name in REGISTRY_FILES:
                # .storage/lovelace_dashboards, lovelace_resources: lists, not dashboards
                self.skipped = f"{path.name} is the list of dashboards/resources, not a dashboard"
                return self._result(path, fmt)

        self.validate(data)
        return self._result(path, fmt)

    def validate(self, data: Any) -> None:
        if data is None:
            self.add("error", None, "", "Empty file")
            return
        if isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict) and "type" not in item and (
                        "sections" in item or "cards" in item or "path" in item):
                    self.view(item, f"[{i}]")
                else:
                    self.card(item, f"[{i}]")
            return
        if not isinstance(data, dict):
            self.add("error", None, "", "Expected a dashboard, a view, a card or a list of cards")
            return
        if "lovelace" in data and isinstance(data["lovelace"], dict):
            self.lovelace_block(data["lovelace"], "lovelace")
            return
        if "views" in data:
            self.dashboard(data)
        elif "strategy" in data and "type" not in data:
            self.strategy(data["strategy"], "strategy", DASHBOARD_STRATEGIES, "dashboard")
        elif "type" in data and data.get("type") not in VIEW_TYPES:
            self.card(data, "")
        elif "sections" in data or "cards" in data or "badges" in data:
            self.view(data, "")
        else:
            self.add("error", data, "", "No `views:`, `sections:` or card `type:` found")

    # -------------------------------------------------- configuration.yaml

    def lovelace_block(self, block: dict, path: str) -> None:
        if block.get("mode") == "yaml":
            self.add("warning", block, f"{path}.mode",
                     "Top-level `lovelace: mode: yaml` is deprecated (repair "
                     "`yaml_mode_deprecated`). Use `resource_mode: yaml` for resources "
                     "and declare the main dashboard under `dashboards: lovelace: "
                     "{mode: yaml, filename: ui-lovelace.yaml}`", since="2026.2")
        dashboards = block.get("dashboards")
        if isinstance(dashboards, dict):
            for key, conf in dashboards.items():
                p = f"{path}.dashboards.{key}"
                if key != "lovelace" and "-" not in str(key):
                    self.add("error", dashboards, p,
                             "Dashboard keys need a hyphen (e.g. `my-home`); only "
                             "`lovelace` is allowed without one")
                if isinstance(conf, dict) and conf.get("mode") == "yaml" and not conf.get("filename"):
                    self.add("error", conf, p, "YAML dashboard needs `filename:`")
        resources = block.get("resources")
        if isinstance(resources, list):
            for i, res in enumerate(resources):
                if isinstance(res, dict) and res.get("type") not in ("module", "js", "css", "html"):
                    self.add("warning", res, f"{path}.resources[{i}]",
                             "Resource `type` should be `module` (or `css`)")

    # ------------------------------------------------------------ dashboard

    def dashboard(self, data: dict) -> None:
        views = data.get("views")
        if not isinstance(views, list):
            if not isinstance(views, HATag):
                self.add("error", data, "views", "`views` must be a list")
            return
        for i, view in enumerate(views):
            self.view(view, f"views[{i}]")

    def view(self, view: Any, path: str) -> None:
        if isinstance(view, (HATag, str)):
            return  # !include of a view file
        if not isinstance(view, dict):
            self.add("error", None, path, "A view must be a mapping")
            return
        self.views += 1

        if "strategy" in view:
            self.strategy(view["strategy"], f"{path}.strategy", VIEW_STRATEGIES, "view")
            return

        vtype = view.get("type")
        if vtype is None:
            if view.get("panel"):
                vtype = "panel"
            elif "sections" in view:
                vtype = "sections"
            elif "cards" in view:
                vtype = "masonry"
                self.add("info", view, path,
                         "View with `cards:` and no `type:` is a masonry view; new "
                         "dashboards use `type: sections`", since="2024.11")
            else:
                vtype = "sections"
        elif isinstance(vtype, str) and not vtype.startswith("custom:") and vtype not in VIEW_TYPES:
            self.add("warning", view, f"{path}.type", f"Unknown view type '{vtype}'")

        if vtype == "sections" and "cards" in view and "sections" not in view:
            self.add("warning", view, f"{path}.cards",
                     "A sections view ignores `cards:`; put cards inside `sections:`")

        if not view.get("title") and not view.get("path") and not view.get("icon"):
            self.add("info", view, path, "View has no `title`, `icon` or `path`")

        for i, badge in enumerate(self._list(view, "badges", path)):
            self.badge(badge, f"{path}.badges[{i}]")

        for key in ("header", "footer"):
            block = view.get(key)
            if isinstance(block, dict):
                if key == "header":
                    self._enum(block, "layout", {"start", "center", "responsive"}, f"{path}.header")
                    self._enum(block, "badges_position", {"bottom", "top"}, f"{path}.header")
                    self._enum(block, "badges_wrap", {"wrap", "scroll"}, f"{path}.header")
                if "card" in block:
                    self.card(block["card"], f"{path}.{key}.card")

        for i, section in enumerate(self._list(view, "sections", path)):
            self.section(section, f"{path}.sections[{i}]")

        cards = view.get("cards")
        if isinstance(cards, list):
            for i, card in enumerate(cards):
                self.card(card, f"{path}.cards[{i}]")

        self.conditions(view.get("visibility"), f"{path}.visibility", view)

    def section(self, section: Any, path: str) -> None:
        if isinstance(section, (HATag, str)):
            return
        if not isinstance(section, dict):
            self.add("error", None, path, "A section must be a mapping")
            return
        self.sections += 1
        if "strategy" in section:
            self.strategy(section["strategy"], f"{path}.strategy", SECTION_STRATEGIES, "section")
            self.conditions(section.get("visibility"), f"{path}.visibility", section)
            return
        stype = section.get("type", "grid")
        if isinstance(stype, str) and stype != "grid" and not stype.startswith("custom:"):
            self.add("warning", section, f"{path}.type", f"Unknown section type '{stype}' (use `grid`)")
        if "title" in section:
            self.add("info", section, f"{path}.title",
                     "Section `title:` is deprecated; start the section with a "
                     "`type: heading` card", since="2024.10")
        span = section.get("column_span")
        if span is not None and not (isinstance(span, int) and 1 <= span <= 4):
            self.add("warning", section, f"{path}.column_span", "`column_span` must be 1-4")
        self.conditions(section.get("visibility"), f"{path}.visibility", section)
        for i, card in enumerate(self._list(section, "cards", path)):
            self.card(card, f"{path}.cards[{i}]")

    def strategy(self, strat: Any, path: str, known: Set[str], kind: str) -> None:
        if not isinstance(strat, dict):
            self.add("error", None, path, "`strategy` must be a mapping with `type`")
            return
        stype = strat.get("type")
        if not stype:
            self.add("error", strat, path, "Strategy is missing `type`")
        elif isinstance(stype, str) and not stype.startswith("custom:") and stype not in known:
            self.add("warning", strat, f"{path}.type", f"Unknown {kind} strategy '{stype}'")
        if stype == "device" and not strat.get("device_id"):
            self.add("warning", strat, path, "`device` section strategy needs `device_id`")
        if stype == "common-controls" and ("title" in strat or "icon" in strat):
            self.add("info", strat, path,
                     "`title`/`icon` on common-controls are deprecated; use `heading:`")
        self.scan_entities(strat, path)

    # ---------------------------------------------------------------- cards

    def card(self, card: Any, path: str, in_custom: bool = False) -> None:
        if isinstance(card, (HATag, str)) and not isinstance(card, dict):
            if isinstance(card, HATag):
                return  # !include card.yaml
            self.add("error", None, path, f"Card must be a mapping, got string '{card}'")
            return
        if not isinstance(card, dict):
            self.add("error", None, path, "Card must be a mapping")
            return
        if not self._once(card):
            return

        ctype = card.get("type")
        if not ctype:
            self.add("error", card, path, "Card is missing `type`")
            return
        if not isinstance(ctype, str):
            self.add("error", card, f"{path}.type", "Card `type` must be a string")
            return

        self.card_types[ctype] = self.card_types.get(ctype, 0) + 1
        custom = ctype.startswith("custom:")
        if custom:
            self.custom_cards.add(ctype)
        elif ctype in MISNAMED_CARDS:
            self.add("warning", card, f"{path}.type",
                     f"'{ctype}' is not a card type: {MISNAMED_CARDS[ctype]}")
        elif ctype not in BUILTIN_CARDS:
            self.add("warning", card, f"{path}.type", f"Unknown card type '{ctype}'")

        self.layout(card, path)

        if "state_color" in card and not custom:
            self.add("info", card, f"{path}.state_color",
                     "`state_color` is being replaced by `color:` (`state`, `none`, a "
                     "theme color name or hex)")

        self.conditions(card.get("visibility"), f"{path}.visibility", card)

        # --- nested cards first so their own paths are recorded
        if ctype in NESTED_CARDS_KEY or custom:
            subs = card.get("cards") if isinstance(card.get("cards"), list) else []
            for i, sub in enumerate(subs):
                if custom and not (isinstance(sub, dict) and "type" in sub):
                    continue
                self.card(sub, f"{path}.cards[{i}]", in_custom=custom)
        if ctype in ("conditional", "entity-filter") or custom:
            sub = card.get("card")
            if sub is not None and (not custom or isinstance(sub, dict) and "type" in sub):
                self.card(sub, f"{path}.card", in_custom=custom)

        # --- per type rules
        if ctype == "conditional":
            if not card.get("conditions"):
                self.add("error", card, path, "Conditional card requires `conditions`")
            else:
                self.conditions(card["conditions"], f"{path}.conditions", card)
            if "card" not in card:
                self.add("error", card, path, "Conditional card requires `card`")
        elif ctype in NESTED_CARDS_KEY:
            if not isinstance(card.get("cards"), list):
                self.add("error", card, path, f"`{ctype}` needs a `cards:` list")
        elif ctype == "entity-filter":
            if "card" in card and "conditions" not in card and "state_filter" not in card:
                self.add("warning", card, path, "entity-filter needs `conditions:` (or legacy `state_filter:`)")
            if isinstance(card.get("conditions"), list):
                self.conditions(card["conditions"], f"{path}.conditions", card, filter_mode=True)
        elif ctype == "heading":
            if "entities" in card:
                self.add("info", card, f"{path}.entities",
                         "Heading card `entities:` is deprecated; use `badges:`")
            for key in ("badges", "entities"):
                for i, badge in enumerate(self._list(card, key, path)):
                    self.heading_badge(badge, f"{path}.{key}[{i}]")
            self._enum(card, "heading_style", {"title", "subtitle"}, path)
        elif ctype == "area":
            if "show_camera" in card:
                self.add("warning", card, f"{path}.show_camera",
                         "`show_camera` is deprecated; use `display_type: camera`", since="2025.7")
            if "navigation_path" in card:
                self.add("info", card, f"{path}.navigation_path",
                         "Area card `navigation_path` is converted to `tap_action: "
                         "{action: navigate, navigation_path: ...}`; write the tap_action", since="2025.7")
            self._enum(card, "display_type", {"compact", "icon", "picture", "camera"}, path)
            if not card.get("area"):
                self.add("error", card, path, "Area card requires `area`")
        elif ctype == "logbook":
            if "entities" in card:
                self.add("info", card, f"{path}.entities",
                         "Logbook card `entities:` is replaced by `target:` "
                         "(entity_id, device_id, area_id, label_id)", since="2025.1")
        elif ctype == "picture-elements":
            self.picture_elements(card.get("elements"), f"{path}.elements")
        elif ctype == "tile":
            if not card.get("entity"):
                self.add("error", card, path, "Tile card requires `entity`")
            self._enum(card, "features_position", {"bottom", "inline"}, path)

        # Custom cards define their own options (`features:`, `entity: ''`...):
        # only their nested cards and actions are checked.
        if "features" in card and isinstance(card["features"], list) and not custom:
            for i, feat in enumerate(card["features"]):
                self.feature(feat, f"{path}.features[{i}]", custom)

        self.scan_actions(card, path, custom or in_custom)
        if not custom:
            self.scan_entities(card, path)

    def layout(self, node: dict, path: str) -> None:
        lo = node.get("layout_options")
        if lo is not None:
            hint = ""
            if isinstance(lo, dict):
                parts = []
                gc = lo.get("grid_columns")
                if isinstance(gc, int):
                    parts.append(f"columns: {gc * 3}")
                elif gc == "full":
                    parts.append("columns: full")
                gr = lo.get("grid_rows")
                if gr is not None:
                    parts.append(f"rows: {gr}")
                if parts:
                    hint = f" Here: `grid_options: {{{', '.join(parts)}}}`."
            self.add("warning", node, f"{path}.layout_options",
                     "`layout_options` is replaced by `grid_options` on a 12-column grid "
                     "(grid_columns x3 = columns; grid_rows = rows)." + hint, since="2024.11")
        go = node.get("grid_options")
        if isinstance(go, dict):
            cols = go.get("columns")
            if cols is not None and cols != "full" and not (isinstance(cols, int) and 1 <= cols <= 12):
                self.add("warning", node, f"{path}.grid_options.columns",
                         f"`columns` must be 1-12 or `full` (got {cols!r})")
            rows = go.get("rows")
            if rows is not None and rows != "auto" and not (isinstance(rows, int) and rows >= 1):
                self.add("warning", node, f"{path}.grid_options.rows",
                         f"`rows` must be a positive number or `auto` (got {rows!r})")

    # --------------------------------------------------------------- badges

    def badge(self, badge: Any, path: str) -> None:
        if isinstance(badge, str):
            if not isinstance(badge, HATag):
                self.add("info", None, path,
                         f"Bare entity badge '{badge}' is converted to `type: entity`; write "
                         "`- type: entity` + `entity:`", since="2024.8")
                self.entity_ref(badge, path, None)
            return
        if not isinstance(badge, dict) or not self._once(badge):
            return
        btype = badge.get("type", "entity")
        if isinstance(btype, str) and not btype.startswith("custom:") and btype not in BADGE_TYPES:
            self.add("warning", badge, f"{path}.type", f"Unknown badge type '{btype}'")
        if "display_type" in badge:
            self.add("info", badge, f"{path}.display_type",
                     "Badge `display_type` is replaced by `show_name`, `show_state` and "
                     "`show_icon`", since="2024.9")
        if btype == "entity" and not badge.get("entity"):
            self.add("error", badge, path, "Entity badge requires `entity`")
        self.conditions(badge.get("visibility"), f"{path}.visibility", badge)
        self.scan_actions(badge, path, isinstance(btype, str) and btype.startswith("custom:"))
        self.scan_entities(badge, path)

    def heading_badge(self, badge: Any, path: str) -> None:
        if isinstance(badge, str):
            self.entity_ref(badge, path, None)
            return
        if not isinstance(badge, dict) or not self._once(badge):
            return
        btype = badge.get("type", "entity")
        if isinstance(btype, str) and not btype.startswith("custom:") and btype not in HEADING_BADGE_TYPES:
            self.add("warning", badge, f"{path}.type",
                     f"Unknown heading badge type '{btype}' (use `entity` or `button`)")
        if btype == "entity" and not badge.get("entity"):
            self.add("error", badge, path, "Heading entity badge requires `entity`")
        self.conditions(badge.get("visibility"), f"{path}.visibility", badge)
        self.scan_actions(badge, path, False)
        self.scan_entities(badge, path)

    # ------------------------------------------------------------- features

    def feature(self, feat: Any, path: str, custom_card: bool) -> None:
        if not isinstance(feat, dict):
            self.add("error", None, path, "Feature must be a mapping with `type`")
            return
        ftype = feat.get("type")
        if not ftype:
            self.add("error", feat, path, "Feature is missing `type`")
        elif isinstance(ftype, str) and not ftype.startswith("custom:") and ftype not in FEATURE_TYPES:
            self.add("warning", feat, f"{path}.type", f"Unknown tile feature '{ftype}'")

    # ------------------------------------------------------ picture-elements

    def picture_elements(self, elements: Any, path: str) -> None:
        if not isinstance(elements, list):
            return
        for i, el in enumerate(elements):
            p = f"{path}[{i}]"
            if not isinstance(el, dict):
                continue
            etype = el.get("type")
            if not etype:
                self.add("error", el, p, "Picture element is missing `type`")
            elif isinstance(etype, str) and not etype.startswith("custom:") and etype not in PICTURE_ELEMENTS:
                self.add("warning", el, f"{p}.type", f"Unknown picture element '{etype}'")
            if etype == "conditional":
                self.conditions(el.get("conditions"), f"{p}.conditions", el)
                self.picture_elements(el.get("elements"), f"{p}.elements")

    # -------------------------------------------------------------- actions

    def scan_actions(self, node: Any, path: str, custom: bool) -> None:
        """Find every `*_action` mapping below `node` (rows, elements, chips...)."""
        if isinstance(node, dict):
            for key, value in node.items():
                child = f"{path}.{key}" if path else str(key)
                if (key in ACTION_KEYS or str(key).endswith("_action")) and isinstance(value, dict):
                    self.action(value, child, custom)
                elif isinstance(value, (dict, list)):
                    self.scan_actions(value, child, custom)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                self.scan_actions(item, f"{path}[{i}]", custom)

    def action(self, act: dict, path: str, custom: bool) -> None:
        if not self._once(act):
            return
        kind = act.get("action")
        if kind is None:
            return
        if isinstance(kind, str) and _is_dynamic(kind):
            return
        if kind not in ACTIONS:
            if not custom:
                self.add("warning", act, f"{path}.action", f"Unknown action '{kind}'")
            return

        if kind == "call-service":
            target = act.get("service") or act.get("perform_action")
            if not target:
                self.add("error", act, path, "`call-service` action has no `service`")
            self.add("warning", act, f"{path}.action",
                     "`action: call-service` is deprecated; use `action: perform-action` "
                     f"with `perform_action: {target or '<domain.action>'}`, `data:` and "
                     "`target:`", since="2024.8")
        elif "service" in act:
            self.add("warning", act, f"{path}.service",
                     "`service:` is deprecated in actions; use `perform_action:`", since="2024.8")
        if "service_data" in act:
            self.add("warning", act, f"{path}.service_data",
                     "`service_data:` is deprecated; use `data:` (and `target:` for "
                     "entity_id/area_id/device_id)", since="2024.8")

        if kind == "perform-action" and not act.get("perform_action") and not act.get("service"):
            self.add("error", act, path, "`perform-action` requires `perform_action: domain.action`")
        elif kind == "navigate" and not act.get("navigation_path"):
            self.add("error", act, path, "`navigate` requires `navigation_path`")
        elif kind == "url" and not act.get("url_path"):
            self.add("error", act, path, "`url` requires `url_path`")

        name = act.get("perform_action") or act.get("service")
        if isinstance(name, str) and not _is_dynamic(name) and not re.match(r"^[a-z0-9_]+\.[a-z0-9_]+$", name):
            self.add("warning", act, path, f"Action name '{name}' should look like `domain.action`")

    # ----------------------------------------------------------- conditions

    def conditions(self, conds: Any, path: str, owner: Any, filter_mode: bool = False) -> None:
        if conds is None:
            return
        if not isinstance(conds, list):
            self.add("error", owner, path, "Conditions must be a list")
            return
        for i, cond in enumerate(conds):
            p = f"{path}[{i}]"
            if isinstance(cond, str) or not isinstance(cond, dict):
                continue  # entity-filter accepts plain state strings
            ctype = cond.get("condition")
            if ctype is None:
                if not filter_mode and "entity" in cond:
                    self.add("info", cond, p,
                             "Legacy condition without `condition:`; write "
                             "`condition: state` + `entity` + `state`")
                continue
            if ctype in CONDITIONS_WITH_CHILDREN:
                if not isinstance(cond.get("conditions"), list):
                    self.add("error", cond, p, f"`{ctype}` condition requires a `conditions` list")
                else:
                    self.conditions(cond["conditions"], f"{p}.conditions", cond, filter_mode)
            elif ctype in CONDITIONS_WITH_ENTITY and not filter_mode:
                if not cond.get("entity") and not cond.get("entity_id"):
                    self.add("error", cond, p, f"`{ctype}` condition requires `entity`")
            elif ctype == "screen" and not cond.get("media_query"):
                self.add("error", cond, p, "`screen` condition requires `media_query`")
            elif ctype == "user" and not cond.get("users"):
                self.add("error", cond, p, "`user` condition requires `users` (user ids)")

    # ------------------------------------------------------------- entities

    def entity_ref(self, value: Any, path: str, node: Any) -> None:
        if not isinstance(value, str) or not value or _is_dynamic(value):
            return
        self.entities.add(value)
        if not ENTITY_ID_RE.match(value) and path not in self._warned_entities:
            self._warned_entities.add(path)
            self.add("warning", node, path,
                     f"Entity id '{value}' does not look like `domain.object_id` "
                     "(lowercase, digits, underscores)")

    def scan_entities(self, node: Any, path: str, parent_key: str = "") -> None:
        """Collect `entity`, `entities` and `target.entity_id` values below `node`."""
        if isinstance(node, dict):
            for key, value in node.items():
                child = f"{path}.{key}" if path else str(key)
                if key == "entity":
                    self.entity_ref(value, child, node)
                elif key == "entities" and isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, str):
                            self.entity_ref(item, f"{child}[{i}]", node)
                        elif isinstance(item, dict):
                            self.scan_entities(item, f"{child}[{i}]", key)
                elif key == "entity_id" and parent_key in ("target", "data", ""):
                    vals = value if isinstance(value, list) else [value]
                    for v in vals:
                        if v not in ("all", "none"):
                            self.entity_ref(v, child, node)
                elif key in ("filter", "include", "exclude"):
                    continue  # auto-entities style filters use wildcards
                elif isinstance(value, (dict, list)) and key not in ("card", "cards"):
                    self.scan_entities(value, child, str(key))
        elif isinstance(node, list):
            for i, item in enumerate(node):
                self.scan_entities(item, f"{path}[{i}]", parent_key)

    # ---------------------------------------------------------------- misc

    def _list(self, node: dict, key: str, path: str) -> list:
        value = node.get(key)
        if value is None or isinstance(value, HATag):
            return []
        if not isinstance(value, list):
            self.add("error", node, f"{path}.{key}" if path else key, f"`{key}` must be a list")
            return []
        return value

    def _enum(self, node: dict, key: str, allowed: Set[str], path: str) -> None:
        value = node.get(key)
        if value is not None and value not in allowed:
            self.add("warning", node, f"{path}.{key}" if path else key,
                     f"`{key}: {value}` is not one of {', '.join(sorted(allowed))}")

    def _result(self, path: Path, fmt: str) -> Dict[str, Any]:
        order = {"error": 0, "warning": 1, "info": 2}
        self.findings.sort(key=lambda f: (f["line"] or 0, order[f["level"]]))

        def flat(f: Dict[str, Any]) -> str:
            prefix = f"Line {f['line']}: " if f["line"] else ""
            since = f" (since {f['since']})" if f["since"] else ""
            return f"{prefix}{f['path']}: {f['message']}{since}"

        errors = [flat(f) for f in self.findings if f["level"] == "error"]
        warnings = [flat(f) for f in self.findings if f["level"] == "warning"]
        valid = not errors and not (self.strict and warnings)
        return {
            "valid": valid,
            "file": str(path.absolute()),
            "format": fmt,
            **({"skipped": self.skipped} if self.skipped else {}),
            "summary": {
                "views": self.views,
                "sections": self.sections,
                "total_cards": sum(self.card_types.values()),
                "card_types": dict(sorted(self.card_types.items())),
                "custom_cards": sorted(self.custom_cards),
                "entities_referenced": len(self.entities),
            },
            "findings": self.findings,
            "errors": errors,
            "warnings": warnings,
        }


def main(argv: List[str]) -> int:
    ensure_yaml()
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(json.dumps({
            "error": "Usage: lovelace_validator.py <file> [--strict]",
            "examples": [
                "python3 lovelace_validator.py ui-lovelace.yaml",
                "python3 lovelace_validator.py /config/.storage/lovelace --strict",
                "python3 lovelace_validator.py card-snippet.yaml",
            ],
        }, indent=2))
        return 1
    results = []
    for arg in args:
        if Path(arg).name in REGISTRY_FILES:
            continue  # `.storage/lovelace*` globs also match the registries
        results.append(LovelaceValidator(strict="--strict" in argv).validate_file(arg))
    if len(results) == 1:
        print(json.dumps(results[0], indent=2, ensure_ascii=False))
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if all(r["valid"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
