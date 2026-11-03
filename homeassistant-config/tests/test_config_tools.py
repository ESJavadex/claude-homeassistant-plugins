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
