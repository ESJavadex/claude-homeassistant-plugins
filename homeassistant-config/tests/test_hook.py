"""Tests for hooks/validate_ha_yaml.py, fed the same JSON Claude Code sends on stdin."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
HOOK = PLUGIN / "hooks" / "validate_ha_yaml.py"


def run_hook(event, env_root=True):
    env = dict(os.environ)
    if env_root:
        env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN)
    out = subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps(event), capture_output=True, text=True, env=env
    )
    return out.returncode, out.stdout.strip(), out.stderr.strip()


class HookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "configuration.yaml").write_text("default_config:\n")

    def tearDown(self):
        self.tmp.cleanup()

    def event(self, name, tool="Edit"):
        return {
            "hook_event_name": "PostToolUse",
            "tool_name": tool,
            "cwd": str(self.root),
            "tool_input": {"file_path": str(self.root / name), "old_string": "a", "new_string": "b"},
            "tool_response": {"filePath": str(self.root / name)},
        }

    def write(self, name, text):
        (self.root / name).write_text(text)

    def test_valid_file_is_silent(self):
        self.write("automations.yaml", "- id: a\n  triggers:\n    - trigger: state\n      entity_id: sun.sun\n  actions: []\n")
        code, out, err = run_hook(self.event("automations.yaml"))
        self.assertEqual((code, out), (0, ""))

    def test_error_blocks_with_reason(self):
        self.write("configuration.yaml", "sensor:\n  - platform: template\n    sensors: {}\n")
        code, out, _ = run_hook(self.event("configuration.yaml", tool="Write"))
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["decision"], "block")
        self.assertIn("Legacy template sensor", payload["reason"])

    def test_syntax_error_blocks(self):
        self.write("scripts.yaml", "a: [1, 2\n")
        code, out, _ = run_hook(self.event("scripts.yaml"))
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_warning_becomes_context(self):
        self.write("configuration.yaml", "http:\n  server_port: 8123\n")
        code, out, _ = run_hook(self.event("configuration.yaml"))
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("http", ctx)

    def test_info_only_is_silent(self):
        self.write("automations.yaml", "- id: a\n  trigger:\n    - platform: state\n      entity_id: sun.sun\n  action:\n    - service: light.turn_on\n")
        code, out, _ = run_hook(self.event("automations.yaml"))
        self.assertEqual((code, out), (0, ""))

    def test_non_yaml_and_bad_input_are_ignored(self):
        self.assertEqual(run_hook({"tool_input": {"file_path": "/tmp/x.py"}})[:2], (0, ""))
        out = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, text=True)
        self.assertEqual((out.returncode, out.stdout), (0, ""))

    def test_works_without_plugin_root_env(self):
        self.write("scripts.yaml", "a: [1, 2\n")
        code, out, _ = run_hook(self.event("scripts.yaml"), env_root=False)
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_dashboard_gets_dashboard_rules(self):
        self.write("ui-lovelace.yaml", (
            "views:\n  - title: Home\n    type: sections\n    sections:\n      - type: grid\n        cards:\n"
            "          - type: button\n            entity: light.sofa\n            tap_action:\n"
            "              action: call-service\n              service: light.toggle\n"
        ))
        code, out, _ = run_hook(self.event("ui-lovelace.yaml"))
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("call-service", ctx)

    def test_esphome_template_sensor_is_not_flagged(self):
        (self.root / "esphome").mkdir()
        self.write("esphome/node.yaml", "esphome:\n  name: n\nsensor:\n  - platform: template\n    lambda: !lambda return 1;\n")
        code, out, _ = run_hook(self.event("esphome/node.yaml"))
        self.assertEqual((code, out), (0, ""))


if __name__ == "__main__":
    unittest.main()
