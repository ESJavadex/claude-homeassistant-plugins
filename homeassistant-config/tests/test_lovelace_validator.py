"""Tests for skills/homeassistant-config/scripts/lovelace_validator.py.

Run: python3 -m unittest discover -s homeassistant-config/tests
"""

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent
SCRIPTS = PLUGIN / "skills" / "homeassistant-config" / "scripts"
EXAMPLES = PLUGIN / "skills" / "homeassistant-config" / "examples"
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from lovelace_validator import LovelaceValidator  # noqa: E402


def run_file(path, strict=False):
    return LovelaceValidator(strict=strict).validate_file(str(path))


def run_text(text, suffix=".yaml", strict=False):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"snippet{suffix}"
        path.write_text(textwrap.dedent(text), encoding="utf-8")
        return run_file(path, strict=strict)


def messages(result, level=None):
    return [f["message"] for f in result["findings"] if level is None or f["level"] == level]


def has(result, level, needle):
    return any(needle in m for m in messages(result, level))


class ModernFixture(unittest.TestCase):
    def test_modern_has_no_errors_or_warnings(self):
        result = run_file(FIXTURES / "lovelace_modern.yaml", strict=True)
        self.assertTrue(result["valid"], result["findings"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])

    def test_summary(self):
        s = run_file(FIXTURES / "lovelace_modern.yaml")["summary"]
        self.assertEqual(s["views"], 1)
        self.assertEqual(s["sections"], 3)
        self.assertEqual(s["card_types"]["tile"], 4)  # incl. footer + conditional child
        self.assertIn("clock", s["card_types"])  # nested in vertical-stack
        self.assertEqual(s["custom_cards"], [])
        self.assertGreater(s["entities_referenced"], 5)

    def test_output_shape(self):
        result = run_file(FIXTURES / "lovelace_legacy.yaml")
        for key in ("valid", "file", "format", "summary", "findings", "errors", "warnings"):
            self.assertIn(key, result)
        for f in result["findings"]:
            self.assertEqual(set(f), {"level", "line", "path", "message", "since"})
            self.assertIn(f["level"], ("error", "warning", "info"))


class LegacyFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_file(FIXTURES / "lovelace_legacy.yaml")
        cls.by_since = {}
        for f in cls.result["findings"]:
            cls.by_since.setdefault(f["since"], []).append(f)

    def test_valid_without_strict_but_not_with_strict(self):
        self.assertTrue(self.result["valid"], self.result["errors"])
        self.assertFalse(run_file(FIXTURES / "lovelace_legacy.yaml", strict=True)["valid"])

    def test_call_service_and_service_data(self):
        self.assertTrue(has(self.result, "warning", "call-service"))
        self.assertTrue(has(self.result, "warning", "service_data"))
        self.assertTrue(has(self.result, "warning", "`service:` is deprecated"))
        self.assertTrue(all(f["since"] == "2024.8" for f in self.result["findings"]
                            if "call-service" in f["message"]))

    def test_layout_options_conversion(self):
        f = [f for f in self.result["findings"] if "layout_options" in f["path"]]
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["level"], "warning")
        self.assertEqual(f[0]["since"], "2024.11")
        self.assertIn("columns: 6", f[0]["message"])
        self.assertIsInstance(f[0]["line"], int)

    def test_infos(self):
        self.assertTrue(has(self.result, "info", "Section `title:`"))
        self.assertTrue(has(self.result, "info", "Heading card `entities:`"))
        self.assertTrue(has(self.result, "info", "state_color"))
        self.assertTrue(has(self.result, "info", "navigation_path"))
        self.assertTrue(has(self.result, "info", "Logbook"))
        self.assertTrue(has(self.result, "info", "display_type"))
        self.assertTrue(has(self.result, "info", "masonry"))

    def test_area_show_camera_warning(self):
        self.assertTrue(has(self.result, "warning", "show_camera"))

    def test_flat_strings(self):
        self.assertTrue(all(w.startswith("Line ") for w in self.result["warnings"]))
        self.assertEqual(len(self.result["warnings"]),
                         len(messages(self.result, "warning")))


class Errors(unittest.TestCase):
    def test_action_errors(self):
        r = run_text("""
            type: vertical-stack
            cards:
              - type: button
                tap_action: {action: navigate}
              - type: button
                tap_action: {action: url}
              - type: button
                tap_action: {action: perform-action}
        """)
        self.assertFalse(r["valid"])
        self.assertTrue(has(r, "error", "navigation_path"))
        self.assertTrue(has(r, "error", "url_path"))
        self.assertTrue(has(r, "error", "perform_action"))

    def test_conditional_without_conditions(self):
        r = run_text("""
            type: conditional
            card: {type: tile, entity: light.a}
        """)
        self.assertTrue(has(r, "error", "requires `conditions`"))

    def test_card_without_type(self):
        r = run_text("""
            - entity: light.a
            - type: tile
              entity: light.b
        """)
        self.assertTrue(has(r, "error", "missing `type`"))
        self.assertEqual(r["summary"]["total_cards"], 1)

    def test_bad_entity_id_and_templates(self):
        r = run_text("""
            type: entities
            entities:
              - Light.Kitchen Lamp
              - entity: sensor.ok
            tap_action:
              action: perform-action
              perform_action: light.turn_on
              target:
                entity_id: "{{ states.light | map(attribute='entity_id') | list }}"
        """)
        bad = [f for f in r["findings"] if "Entity id" in f["message"]]
        self.assertEqual(len(bad), 1)
        self.assertIn("Light.Kitchen Lamp", bad[0]["message"])

    def test_unknown_types(self):
        r = run_text("""
            type: grid
            cards:
              - type: tile
                entity: light.a
                features:
                  - type: light-sparkle
              - type: webpage
                url: https://example.com
              - type: made-up
              - type: custom:whatever-card
        """)
        self.assertTrue(has(r, "warning", "Unknown tile feature 'light-sparkle'"))
        self.assertTrue(has(r, "warning", "`iframe`"))
        self.assertTrue(has(r, "warning", "Unknown card type 'made-up'"))
        self.assertFalse(has(r, "warning", "whatever"))
        self.assertEqual(r["summary"]["custom_cards"], ["custom:whatever-card"])

    def test_grid_options_range(self):
        r = run_text("""
            type: tile
            entity: light.a
            grid_options: {columns: 13, rows: auto}
        """)
        self.assertTrue(has(r, "warning", "1-12"))


class Formats(unittest.TestCase):
    def test_storage_json(self):
        data = {"version": 1, "key": "lovelace", "data": {"config": {"views": [{
            "type": "sections", "title": "A",
            "sections": [{"type": "grid", "cards": [
                {"type": "tile", "entity": "light.a",
                 "tap_action": {"action": "call-service", "service": "light.toggle"}}]}]}]}}}
        r = run_text(json.dumps(data), suffix="")
        self.assertEqual(r["format"], "json")
        self.assertEqual(r["summary"]["views"], 1)
        f = [f for f in r["findings"] if "call-service" in f["message"]]
        self.assertEqual(len(f), 1)
        self.assertIsNone(f[0]["line"])

    def test_include_tags_parse(self):
        r = run_text("""
            title: Split
            views:
              - !include views/home.yaml
              - title: Inline
                type: sections
                sections:
                  - !include sections/kitchen.yaml
                  - type: grid
                    cards:
                      - !include cards/clock.yaml
        """)
        self.assertEqual(r["format"], "yaml")
        self.assertEqual(r["errors"], [])

    def test_single_view_snippet(self):
        r = run_text("""
            type: sections
            sections:
              - type: grid
                cards:
                  - type: heading
                    heading: Hi
        """)
        self.assertEqual(r["summary"]["views"], 1)
        self.assertEqual(r["summary"]["card_types"], {"heading": 1})

    def test_lovelace_block_mode_yaml(self):
        r = run_text("""
            lovelace:
              mode: yaml
              dashboards:
                myhome:
                  mode: yaml
                  filename: my.yaml
        """)
        self.assertTrue(has(r, "warning", "resource_mode"))
        self.assertTrue(has(r, "error", "hyphen"))

    def test_syntax_error(self):
        r = run_text("views:\n  - title: [unclosed\n")
        self.assertFalse(r["valid"])
        self.assertIsInstance(r["findings"][0]["line"], int)


class Examples(unittest.TestCase):
    def test_examples_clean(self):
        for name in ("lovelace-dashboard.yaml", "lovelace-custom-cards.yaml"):
            with self.subTest(name=name):
                r = run_file(EXAMPLES / name, strict=True)
                self.assertTrue(r["valid"], r["findings"])
                self.assertEqual(r["warnings"], [])

    def test_cli_exit_codes(self):
        script = str(SCRIPTS / "lovelace_validator.py")
        ok = subprocess.run([sys.executable, script, str(FIXTURES / "lovelace_modern.yaml"), "--strict"],
                            capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout)
        json.loads(ok.stdout)
        bad = subprocess.run([sys.executable, script, str(FIXTURES / "lovelace_legacy.yaml"), "--strict"],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)


if __name__ == "__main__":
    unittest.main()
