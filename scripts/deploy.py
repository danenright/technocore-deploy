#!/usr/bin/env python3
"""Bootstrap and deploy the private-origin Technocore Compose stack over SSH."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REQUIRED = {
    "DROPLET_IP",
    "SSH_USER",
    "SSH_KEY_PATH",
    "TECHNOCORE_IMAGE",
    "CLOUDFLARE_TUNNEL_TOKEN",
    "CHAT_PUBLIC_URL",
    "CHAT_SECURITY_CONTACT",
    "CHAT_CLIENT_IP_HEADER",
}
REMOTE_ENV_KEYS = (
    "TECHNOCORE_IMAGE",
    "CLOUDFLARE_TUNNEL_TOKEN",
    "CHAT_PUBLIC_URL",
    "CHAT_SECURITY_CONTACT",
    "CHAT_CLIENT_IP_HEADER",
)
KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not KEY_RE.fullmatch(key):
            raise ValueError(f"invalid environment line {number}")
        if "\n" in value or "\r" in value:
            raise ValueError(f"multiline value refused for {key}")
        values[key] = value
    missing = REQUIRED - values.keys()
    if missing:
        raise ValueError(f"missing required values: {', '.join(sorted(missing))}")
    if len(values["CLOUDFLARE_TUNNEL_TOKEN"]) < 40:
        raise ValueError("Cloudflare tunnel token is unexpectedly short")
    if not Path(values["SSH_KEY_PATH"]).is_file():
        raise ValueError("SSH private key path does not exist")
    return values


def ssh_base(values: dict[str, str]) -> list[str]:
    target = f"{values['SSH_USER']}@{values['DROPLET_IP']}"
    return [
        "ssh",
        "-i",
        values["SSH_KEY_PATH"],
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=20",
        "-o",
        "StrictHostKeyChecking=accept-new",
        target,
    ]


def run(command: list[str], *, stdin: str | None = None) -> None:
    subprocess.run(command, input=stdin, text=True, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provision-env",
        type=Path,
        default=Path.home() / ".config" / "technocore-deploy" / "provision.env",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        values = load_env(args.provision_env)
        ssh = ssh_base(values)

        print("[1/4] Installing or verifying Docker Engine")
        run(ssh + ["bash -s"], stdin=(root / "scripts" / "bootstrap_ubuntu.sh").read_text())

        print("[2/4] Uploading Compose configuration")
        scp = [
            "scp",
            "-i",
            values["SSH_KEY_PATH"],
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            str(root / "compose.yaml"),
            f"{values['SSH_USER']}@{values['DROPLET_IP']}:/opt/technocore/compose.yaml",
        ]
        run(scp)

        print("[3/4] Installing private deployment environment")
        remote_env = "".join(f"{key}={values[key]}\n" for key in REMOTE_ENV_KEYS)
        run(
            ssh + ["umask 077; cat > /opt/technocore/.env; chmod 600 /opt/technocore/.env"],
            stdin=remote_env,
        )

        print("[4/4] Pulling and starting the private-origin stack")
        run(
            ssh
            + [
                "cd /opt/technocore && "
                "docker compose config --quiet && "
                "docker compose pull --quiet && "
                "docker compose up -d --remove-orphans && "
                "docker compose ps"
            ]
        )
        print("Deployment started. If the Cloudflare route was pending, add it after the tunnel is Healthy.")
        return 0
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
