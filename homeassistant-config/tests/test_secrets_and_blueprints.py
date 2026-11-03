"""Credentials never reach the output, and imported blueprints are counted, not listed.

Feedback on plugin 2.1.2 (issue #75 of claude-code-ha): a syntax error in an
ESPHome node quoted a Wi-Fi password, and 57 of 91 info items came from
imported blueprints the user should not edit.

Run: python3 -m unittest discover -s homeassistant-config/tests
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent
SCRIPTS = PLUGIN / "skills" / "homeassistant-config" / "scripts"
HOOK = PLUGIN / "hooks" / "validate_ha_yaml.py"
sys.path.insert(0, str(SCRIPTS))

from ha_yaml import redact  # noqa: E402

PASSWORD = "hunter2-plain-text"
TOKEN = "s3cr3t-url-token"


def run(script, *args):
    out = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True)
    return out.stdout + out.stderr


class RedactTests(unittest.TestCase):
    def test_credential_values_are_masked(self):
        text = (
            "      password: \"abc def\n"
            "  - wifi_password: abc\n"
            "    api_key: sk-123\n"
            "    \"token\": xyz\n"
            "    key: \"base64==\"\n"
            "    url: mqtt://user:pa55@broker:1883\n"
        )
        out = redact(text)
        for value in ("abc def", "abc\n", "sk-123", "xyz", "base64==", "pa55"):
            self.assertNotIn(value, out)
        self.assertIn("mqtt://user:***@broker", out)

    def test_references_and_other_keys_are_kept(self):
        text = "password: !secret wifi_pw\nkey_id: !env_var X\nname: Kitchen\nkeyboard: us\n"
        out = redact(text)
        self.assertIn("!secret wifi_pw", out)
        self.assertIn("name: Kitchen", out)
        self.assertIn("keyboard: us", out)


class NoCredentialsInOutput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "configuration.yaml").write_text("default_config:\n")
        (self.root / "esphome").mkdir()
        # Unclosed quote: the error snippet is the password line
        (self.root / "esphome" / "node.yaml").write_text(
            f"esphome:\n  name: node\nwifi:\n  ssid: home\n  password: \"{PASSWORD}\n"
        )
        (self.root / "ui-lovelace.yaml").write_text(
            f"views:\n  - title: Cam\n    cards:\n      - type: iframe\n        url: \"https://u:{TOKEN}@cam/x\n"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def assertClean(self, out):
        self.assertNotIn(PASSWORD, out)
        self.assertNotIn(TOKEN, out)

    def test_validate_yaml(self):
        out = run("validate_yaml.py", self.root)
        self.assertIn("YAML syntax error", out)
        self.assertClean(out)
        self.assertClean(run("validate_yaml.py", self.root / "esphome" / "node.yaml"))

    def test_check_config(self):
        out = run("check_config.py", self.root, "--include-unloaded")
        self.assertIn("syntax_error", out)
        self.assertClean(out)

    def test_find_duplicates(self):
        out = run("find_duplicates.py", self.root, "--include-unloaded")
        self.assertIn("parse error", out)
        self.assertClean(out)

    def test_lovelace_validator(self):
        out = run("lovelace_validator.py", self.root / "ui-lovelace.yaml")
        self.assertIn("YAML syntax error", out)
        self.assertClean(out)

    def test_hook_block_reason(self):
        path = self.root / "esphome" / "node.yaml"
        event = {"hook_event_name": "PostToolUse", "tool_name": "Write", "cwd": str(self.root),
                 "tool_input": {"file_path": str(path)}}
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(PLUGIN))
        out = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event),
                             capture_output=True, text=True, env=env).stdout
        self.assertEqual(json.loads(out)["decision"], "block")
        self.assertClean(out)


IMPORTED = """\
blueprint:
  name: Motion light
  domain: automation
  source_url: https://github.com/someone/blueprints/motion_light.yaml
  input:
    light:
      selector:
        entity: {}
trigger:
  - platform: state
    entity_id: binary_sensor.x
action:
  - service: light.turn_on
    target: !input light
  - service: light.turn_off
    target: !input light
"""

OWN = """\
blueprint:
  name: My blueprint
  domain: automation
  input:
    light:
      selector:
        entity: {}
triggers:
  - trigger: state
    entity_id: binary_sensor.x
actions:
  - service: light.turn_on
    target: !input light
"""


class ImportedBlueprints(unittest.TestCase):
    def test_counted_per_blueprint_not_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configuration.yaml").write_text("default_config:\n")
            imported = root / "blueprints" / "automation" / "someone" / "motion_light.yaml"
            own = root / "blueprints" / "automation" / "me" / "mine.yaml"
            for path, text in ((imported, IMPORTED), (own, OWN)):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            report = json.loads(run("validate_yaml.py", root, "--quiet"))
            summary = report["summary"]
            self.assertEqual(summary["imported_blueprints"]["count"], 1)
            self.assertGreaterEqual(summary["imported_blueprints"]["info"][str(imported)], 3)
            by_file = {r["file"]: r for r in report["results"]}
            self.assertNotIn(str(imported), by_file)  # nothing left to list
            self.assertTrue(by_file[str(own)]["info"])  # your own blueprint is listed
            self.assertEqual(summary["info"], len(by_file[str(own)]["info"]))


if __name__ == "__main__":
    unittest.main()
