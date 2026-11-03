"""Tests for check_config.py and find_duplicates.py."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "skills" / "homeassistant-config" / "scripts"
FIXTURES = HERE / "fixtures"


def run(script, *args):
    out = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True)
    return out.returncode, json.loads(out.stdout)


OLD_AND_NEW = """\
- id: a
  alias: Porch light old
  trigger:
    - platform: state
      entity_id: binary_sensor.porch
      to: "on"
  action:
    - service: light.turn_on
      target:
        entity_id: light.porch
- id: b
  alias: Porch light new
  triggers:
    - trigger: state
      entity_id: binary_sensor.porch
      to: "on"
  actions:
    - action: light.turn_on
      target:
        entity_id: light.porch
- id: c
  alias: Notify phone at night
  triggers:
    - trigger: time
      at: "23:00:00"
  actions:
    - action: notify.mobile_app_phone
      data:
        message: Night
- id: d
  alias: Battery report
  triggers:
    - trigger: time
      at: "09:00:00"
  actions:
    - action: notify.mobile_app_phone
      data:
        message: Battery
"""


class CheckConfigTests(unittest.TestCase):
    def test_modern_fixture_is_clean(self):
        code, r = run("check_config.py", FIXTURES / "ha_config")
        self.assertEqual(code, 0, r)
        self.assertEqual(r["status"], "ok", r)
        self.assertIn("automation", r["summary"]["domains_found"])
        self.assertEqual(r["summary"]["secrets_referenced"], 1)

    def test_missing_include_secret_and_duplicate_id(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "configuration.yaml").write_text(
                "automation: !include automations.yaml\nscript: !include missing.yaml\n"
                "mqtt:\n  password: !secret mqtt_password\n"
            )
            (root / "automations.yaml").write_text(
                "- id: same\n  alias: One\n  triggers: []\n  actions: []\n"
                "- id: same\n  alias: Two\n  triggers: []\n  actions: []\n"
            )
            (root / "secrets.yaml").write_text("other: x\n")
            code, r = run("check_config.py", root)
            types = {i["type"] for i in r["issues"]}
            self.assertEqual(code, 1)
            self.assertIn("missing_include", types)
            self.assertIn("undefined_secret", types)
            self.assertIn("duplicate_automation_id", types)
            # secret values never appear in the report
            self.assertNotIn('"x"', json.dumps(r))


class FindDuplicatesTests(unittest.TestCase):
    def test_old_and_new_syntax_are_the_same_automation(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "automations.yaml").write_text(OLD_AND_NEW)
            _, r = run("find_duplicates.py", d)
            groups = r["exact_duplicates"]["automations"]
            self.assertEqual(len(groups), 1, r)
            aliases = {i["alias"] for i in groups[0]["items"]}
            self.assertEqual(aliases, {"Porch light old", "Porch light new"})

    def test_notify_action_is_not_a_shared_entity(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "automations.yaml").write_text(OLD_AND_NEW)
            _, r = run("find_duplicates.py", d)
            for group in r["similar_items"]["automations"]:
                self.assertNotIn("notify.mobile_app_phone", group["reason"])

    def test_scripts_yaml_dict_is_scanned(self):
        _, r = run("find_duplicates.py", FIXTURES / "ha_config" / "scripts.yaml")
        self.assertEqual(r["scripts_found"], 1)


if __name__ == "__main__":
    unittest.main()


class FeedbackFixes(unittest.TestCase):
    """False positives reported on real installs (issue #75 of claude-code-ha)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        w = lambda rel, text: (self.root / rel).parent.mkdir(parents=True, exist_ok=True) or (self.root / rel).write_text(text)
        self.w = w
        w("configuration.yaml", (
            "default_config:\n"
            "# api_key: !secret old_key\n"
            "# sensor: !include old_sensors.yaml\n"
            "automation: !include automations.yaml\n"
            "homeassistant:\n  packages: !include_dir_named packages\n"
            "weather:\n  - platform: x\n    key: !secret api_key\n"
        ))
        w("secrets.yaml", "api_key: x\n")
        w("automations.yaml", "- id: '1'\n  alias: A\n  triggers: []\n  actions: []\n")
        w("packages/p.yaml", "input_boolean:\n  guest: {}\n")
        # an old copy that HA does not load
        w("archive/automations.yaml", "- id: '1'\n  alias: A old\n  triggers: []\n  actions: []\n")
        w("drafts/legacy.yaml", "sensor:\n  - platform: template\n    sensors: {}\n")
        # ESPHome keeps its own secrets
        w("esphome/secrets.yaml", "wifi_ssid: x\n")
        w("esphome/node.yaml", "esphome:\n  name: n\nwifi:\n  ssid: !secret wifi_ssid\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_commented_lines_and_esphome_secrets_are_not_issues(self):
        code, report = run("check_config.py", self.root)
        issues = report.get("issues") or []
        self.assertEqual(issues, [], issues)
        self.assertEqual(code, 0)

    def test_undefined_secret_still_found(self):
        self.w("packages/p.yaml", "input_boolean:\n  guest: {}\nsensor:\n  - platform: y\n    k: !secret nope\n")
        _, report = run("check_config.py", self.root)
        self.assertTrue(any("nope" in i["message"] and i["file"] == "packages/p.yaml" for i in report["issues"]))

    def test_unloaded_copies_are_skipped_and_counted(self):
        _, report = run("check_config.py", self.root)
        self.assertEqual(report["not_loaded"]["count"], 2)
        code, report = run("check_config.py", self.root, "--include-unloaded")
        dup = [i for i in report["issues"] if i["type"] == "duplicate_automation_id"]
        self.assertEqual(len(dup), 1)
        # both files are named automations.yaml: the message must tell them apart
        self.assertIn("archive/automations.yaml", dup[0]["file"] + dup[0]["message"])
        self.assertIn("automations.yaml (automation #1)", dup[0]["message"])

    def test_validate_dir_skips_unloaded(self):
        out = subprocess.run([sys.executable, str(SCRIPTS / "validate_yaml.py"), str(self.root), "--quiet"],
                             capture_output=True, text=True)
        summary = json.loads(out.stdout)["summary"]
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(summary["not_loaded"]["count"], 2)
        out = subprocess.run([sys.executable, str(SCRIPTS / "validate_yaml.py"), str(self.root), "--quiet",
                              "--include-unloaded"], capture_output=True, text=True)
        self.assertGreater(json.loads(out.stdout)["summary"]["errors"], 0)

    def test_find_duplicates_ignores_unloaded_copies(self):
        _, report = run("find_duplicates.py", self.root)
        self.assertEqual(report["not_loaded"]["count"], 2)
        self.assertFalse(report.get("exact_duplicates", {}).get("automations"))


class DuplicateFinderFalsePositives(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_blueprints_variables_and_template_entities(self):
        (self.root / "automations.yaml").write_text(
            "- id: a\n  alias: Back remote\n  use_blueprint:\n    path: x/remote.yaml\n    input: {device: aaa}\n"
            "- id: b\n  alias: Vacuum map\n  use_blueprint:\n    path: y/map.yaml\n    input: {camera: c}\n")
        (self.root / "scripts.yaml").write_text(
            "on_x:\n  alias: Power on\n  variables: {state: 'off'}\n  sequence:\n    - action: homeassistant.turn_on\n"
            "      target: {entity_id: '{{ entity }}'}\n"
            "off_x:\n  alias: Power off\n  variables: {state: 'on'}\n  sequence:\n    - action: homeassistant.turn_on\n"
            "      target: {entity_id: '{{ entity }}'}\n")
        (self.root / "templates.yaml").write_text(
            "- triggers:\n    - trigger: time_pattern\n      hours: /1\n  sensor:\n    - name: a\n      state: 1\n"
            "- triggers:\n    - trigger: time_pattern\n      hours: /1\n  sensor:\n    - name: b\n      state: 2\n")
        _, report = run("find_duplicates.py", self.root)
        self.assertEqual(report["exact_duplicates"], {"automations": [], "scripts": []})
        self.assertEqual(report["automations_found"], 2)
        self.assertFalse(report["similar_items"]["automations"])
