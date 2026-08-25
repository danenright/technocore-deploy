from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


deploy = load_module("deploy", ROOT / "scripts" / "deploy.py")
smoke = load_module("smoke", ROOT / "scripts" / "smoke.py")


class ProvisionEnvironmentTests(unittest.TestCase):
    def valid_values(self, key_path: Path) -> dict[str, str]:
        return {
            "DROPLET_IP": "192.0.2.10",
            "SSH_USER": "root",
            "SSH_KEY_PATH": str(key_path),
            "TECHNOCORE_IMAGE": "ghcr.io/flop-labs/technocore-chat:0.7.0",
            "CLOUDFLARE_TUNNEL_TOKEN": "x" * 80,
            "CHAT_PUBLIC_URL": "https://chat.technocore-lab.com",
            "CHAT_SECURITY_CONTACT": "security@example.com",
            "CHAT_CLIENT_IP_HEADER": "cf-connecting-ip",
        }

    def write_env(self, path: Path, values: dict[str, str]) -> None:
        path.write_text("".join(f"{key}={value}\n" for key, value in values.items()))

    def test_valid_environment_loads_without_exposing_extra_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = root / "id_ed25519"
            key.touch()
            env = root / "provision.env"
            expected = self.valid_values(key)
            self.write_env(env, {**expected, "UNRELATED": "ignored-by-remote-env"})

            actual = deploy.load_env(env)

            self.assertEqual(actual["DROPLET_IP"], "192.0.2.10")
            self.assertEqual(actual["CLOUDFLARE_TUNNEL_TOKEN"], "x" * 80)
            self.assertIn("UNRELATED", actual)

    def test_missing_required_value_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = root / "id_ed25519"
            key.touch()
            values = self.valid_values(key)
            values.pop("DROPLET_IP")
            env = root / "provision.env"
            self.write_env(env, values)

            with self.assertRaisesRegex(ValueError, "DROPLET_IP"):
                deploy.load_env(env)

    def test_short_tunnel_token_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = root / "id_ed25519"
            key.touch()
            values = self.valid_values(key)
            values["CLOUDFLARE_TUNNEL_TOKEN"] = "short"
            env = root / "provision.env"
            self.write_env(env, values)

            with self.assertRaisesRegex(ValueError, "unexpectedly short"):
                deploy.load_env(env)

    def test_ssh_command_uses_only_the_selected_key_and_target(self) -> None:
        values = {"SSH_USER": "root", "DROPLET_IP": "192.0.2.10", "SSH_KEY_PATH": "/key"}
        command = deploy.ssh_base(values)
        self.assertIn("/key", command)
        self.assertEqual(command[-1], "root@192.0.2.10")


class ReceiptDurabilityTests(unittest.TestCase):
    def test_committed_receipts_copy_messages_and_label_locators_transient(self) -> None:
        paths = sorted((ROOT / "receipts").glob("*.json"))
        self.assertGreaterEqual(len(paths), 1)
        for path in paths:
            with self.subTest(path=path):
                receipt = json.loads(path.read_text(encoding="utf-8"))
                self.assertNotIn("permalink", receipt)
                self.assertIn("transient_locator", receipt)
                self.assertIn("transient", receipt["durability_note"])
                self.assertEqual(
                    set(receipt["verified_record"]),
                    {"seq", "ts", "from", "text", "nonce"},
                )


class IsolationTests(unittest.TestCase):
    def test_closed_origin_port_passes(self) -> None:
        smoke.assert_origin_closed("127.0.0.1", 1)


if __name__ == "__main__":
    unittest.main()
