"""Tests for validate_yaml.py and ha_yaml.py. Run: python3 -m unittest discover -s homeassistant-config/tests"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent
SCRIPTS = PLUGIN / "skills" / "homeassistant-config" / "scripts"
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import ha_yaml  # noqa: E402
from validate_yaml import HAYamlValidator  # noqa: E402


def findings(path, **kw):
    return HAYamlValidator(**kw).validate_file(str(path))["findings"]


def messages(path, level=None, **kw):
    return [f["message"] for f in findings(path, **kw) if level is None or f["level"] == level]


class LoaderTests(unittest.TestCase):
    def test_ha_tags_parse(self):
        data, dups = ha_yaml.load_text(
            "a: !secret key\nb: !include x.yaml\nc: !include_dir_merge_list d/\ne: !input motion\nf: !env_var HOME\n"
        )
        self.assertEqual(data["a"].tag, "secret")
        self.assertEqual(str(data["b"]), "x.yaml")
        self.assertEqual(dups, [])

    def test_unknown_tags_parse(self):
        data, _ = ha_yaml.load_text("x: !lambda return 1;\ny: !extend z\n")
        self.assertEqual(data["x"].tag, "lambda")

    def test_duplicate_keys_reported_with_line(self):
        _, dups = ha_yaml.load_text("a: 1\nb: 2\na: 3\n")
        self.assertEqual(dups, [("a", 3)])

    def test_line_numbers(self):
        data, _ = ha_yaml.load_text("top:\n  - x: 1\n  - y: 2\n")
        self.assertEqual(ha_yaml.line_of(data["top"][1]), 3)


class ModernConfigTests(unittest.TestCase):
    def test_modern_config_has_no_findings(self):
        for f in ha_yaml.iter_yaml_files(FIXTURES / "ha_config"):
            with self.subTest(file=f.name):
                self.assertEqual(findings(f), [], f)

    def test_esphome_is_not_treated_as_ha(self):
        r = HAYamlValidator().validate_file(str(FIXTURES / "esphome" / "node.yaml"))
        self.assertFalse(r["ha_rules"])
        self.assertTrue(r["valid"])

    def test_directory_cli(self):
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate_yaml.py"), str(FIXTURES / "ha_config")],
            capture_output=True, text=True,
        )
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(json.loads(out.stdout)["summary"]["files"], 6)  # secrets.yaml is never opened


class LegacyConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = findings(FIXTURES / "legacy.yaml", ha_rules=True)
        cls.text = "\n".join(f"{x['level']}|{x['message']}" for x in cls.f)

    def has(self, level, fragment):
        self.assertIn(f"{level}|", self.text)
        self.assertTrue(
            any(x["level"] == level and fragment in x["message"] for x in self.f),
            f"missing {level}: {fragment}\n{self.text}",
        )

    def test_removed_syntax_is_error(self):
        self.has("error", "Legacy template sensor")
        self.has("error", "'value_template' is a legacy template key")
        self.has("error", "MQTT `object_id` was removed")
        self.has("error", "Both 'trigger' and 'triggers'")
        self.has("error", "both 'platform' and 'trigger'")
        self.has("error", "'battery.low' no longer exists")
        self.has("error", "Zone behavior 'any'")
        self.has("error", "both `for` and `attribute`")
        self.has("error", "'climate.target_temperature' no longer exists")
        self.has("error", "`color_temp` is no longer supported")
        self.has("error", "`kelvin` is no longer supported")
        self.has("error", "both 'service' and 'action'")
        self.has("error", "`topic_template` was removed")

    def test_deprecated_syntax_is_warning(self):
        self.has("warning", "lovelace: mode: yaml")
        self.has("warning", "Offset without `offset_type`")
        self.has("warning", "Unquoted on")
        self.has("warning", "`data_template` is long deprecated")
        self.has("warning", "not a valid entity_id")

    def test_old_but_working_syntax_is_info(self):
        self.has("info", "`service: light.turn_on` still works")
        self.has("info", "`platform: state` still works")
        self.has("info", "'condition:' still works")
        self.has("info", "Supervisor actions raise on failure")

    def test_every_finding_has_a_line(self):
        self.assertTrue(all(x["line"] for x in self.f), self.f)


CARD_SNIPPET = """\
type: vertical-stack
cards:
  - type: button
    entity: script.play_sound
    tap_action:
      action: call-service
      service: script.play_sound
"""


class DashboardSnippetTests(unittest.TestCase):
    def test_card_snippet_in_config_folder_is_not_an_automation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "configuration.yaml").write_text("default_config:\n")
            p = Path(d) / "sound_card.yaml"
            p.write_text(CARD_SNIPPET)
            r = HAYamlValidator().validate_file(str(p))
            self.assertTrue(r["dashboard"])
            self.assertFalse(r["ha_rules"])
            self.assertEqual(r["errors"], [])

    def test_mixed_keys_need_two_action_names(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "automations.yaml"
            p.write_text("- id: a\n  triggers: []\n  actions:\n    - service: light.turn_on\n      action: light.turn_off\n")
            self.assertTrue(any("both 'service' and 'action'" in m for m in messages(p, "error")))


class FileProblemTests(unittest.TestCase):
    def test_duplicate_top_level_key(self):
        self.assertTrue(any("Duplicate key 'automation'" in m for m in messages(FIXTURES / "dupes.yaml", "error")))

    def test_tabs(self):
        r = HAYamlValidator().validate_file(str(FIXTURES / "tabs.yaml"))
        self.assertFalse(r["valid"])
        self.assertTrue(any("Tab" in e for e in r["errors"]))

    def test_http_block_in_configuration_yaml(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "configuration.yaml"
            p.write_text("http:\n  server_port: 8123\n")
            self.assertTrue(any("`http:` is imported" in m for m in messages(p, "warning")))


if __name__ == "__main__":
    unittest.main()


class FeedbackRuleTests(unittest.TestCase):
    def check(self, text, **kw):
        return HAYamlValidator(ha_rules=True, **kw).validate_text(text, Path("x.yaml"))

    def test_registry_entity_ids_are_valid(self):
        r = self.check("- id: a\n  triggers: []\n  actions:\n    - device_id: abc\n      domain: light\n"
                       "      entity_id: 0123456789abcdef0123456789abcdef\n      type: turn_on\n", ha_version=None)
        self.assertFalse([w for w in r["warnings"] if "entity_id" in w], r["warnings"])

    def test_collapsed_section_without_default_is_only_info(self):
        r = self.check("blueprint:\n  name: b\n  domain: automation\n  input:\n    s:\n      collapsed: true\n"
                       "      input:\n        x:\n          selector:\n            text: {}\n", ha_version=None)
        self.assertEqual(r["errors"], [])
        self.assertTrue(any("collapsed" in i for i in r["info"]))

    def test_upcoming_rules_on_older_install(self):
        text = "t:\n  fields:\n    d:\n      selector:\n        target:\n          device:\n            integration: hue\n  sequence: []\n"
        r = self.check(text, ha_version="2026.10.4")
        self.assertEqual(r["errors"], [])
        self.assertTrue(r["valid"])
        self.assertEqual(len(r["upcoming"]), 1)
        self.assertEqual(len(self.check(text, ha_version="2026.11.1")["errors"]), 1)
        self.assertEqual(len(self.check(text, ha_version=None)["errors"]), 1)  # unknown: apply all

    def test_note_when_ha_is_newer_than_rules(self):
        self.assertIn("2026.11", self.check("a: 1\n", ha_version="2027.1.0").get("note", ""))
        self.assertNotIn("note", self.check("a: 1\n", ha_version="2026.11.2"))

    def test_version_parsing(self):
        self.assertEqual(ha_yaml.parse_version("2026.11.0b3"), (2026, 11))
        self.assertEqual(ha_yaml.parse_version("2026.9.0.dev20260801"), (2026, 9))
        self.assertIsNone(ha_yaml.parse_version("unknown"))


class PublicConfigFalsePositives(unittest.TestCase):
    """Found by running the checkers over large public configs on GitHub."""

    def check(self, text, name="x.yaml"):
        return HAYamlValidator(ha_rules=True, ha_version=None).validate_text(text, Path(name))

    def test_integration_triggers_take_entity_id(self):
        r = self.check("- id: a\n  triggers:\n    - trigger: webostv.turn_on\n      entity_id: media_player.tv\n"
                       "    - platform: samsungtv.turn_on\n      entity_id: media_player.tv2\n  actions: []\n")
        self.assertFalse([w for w in r["warnings"] if "target" in w], r["warnings"])

    def test_scene_state_booleans_are_fine(self):
        r = self.check("- name: TV\n  entities:\n    light.a:\n      state: on\n      brightness: 10\n")
        self.assertFalse([w for w in r["warnings"] if "boolean" in w], r["warnings"])
        r = self.check("- id: a\n  triggers:\n    - trigger: state\n      entity_id: light.a\n      to: on\n  actions: []\n")
        self.assertTrue([w for w in r["warnings"] if "boolean" in w])

    def test_js_templates_wildcards_and_uppercase_ids(self):
        r = self.check("a:\n  - entity_id: \"[[[ return entity.entity_id ]]]\"\n  - entity_id: light.*\n"
                       "  - entity_id: media_player.LivingRoom\n  - entity_id: not-an-id\n")
        self.assertEqual(len([w for w in r["warnings"] if "entity_id" in w]), 1, r["warnings"])

    def test_merge_from_include_parses(self):
        data, _ = ha_yaml.load_text("<<: !include common.yaml\nesphome:\n  name: x\n")
        self.assertEqual(data["esphome"]["name"], "x")

    def test_lovelace_gen_files_are_skipped(self):
        r = self.check("# lovelace_gen\n{% raw %}\ntype: x\n{% endraw %}\n")
        self.assertIn("skipped", r)
        self.assertTrue(r["valid"])

    def test_absolute_config_includes_map_to_the_config_folder(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "configuration.yaml").write_text("lovelace: !include /config/lovelace.yaml\n")
            (root / "lovelace.yaml").write_text("dashboards:\n  dash-a:\n    mode: yaml\n    filename: ui-a.yaml\n")
            (root / "ui-a.yaml").write_text("views:\n  - cards: !include /config/cards.yaml\n")
            (root / "cards.yaml").write_text("- type: tile\n  entity: light.a\n")
            (root / "old.yaml").write_text("a: 1\n")
            loaded = {p.name for p in ha_yaml.loaded_files(root)}
            self.assertEqual(loaded, {"configuration.yaml", "lovelace.yaml", "ui-a.yaml", "cards.yaml"})
