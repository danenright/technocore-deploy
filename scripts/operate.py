#!/usr/bin/env python3
"""Inspect, back up, or restore the Technocore deployment over SSH."""

from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

import deploy

REMOTE_ROOT = "/opt/technocore"
VOLUME = "technocore-lab_technocore-data"
BACKUP_IMAGE = (
    "busybox:1.37.0@sha256:"
    "9db7b59979c38555a39def84a31fb98b5296952f9e3afd4f6f11f05b07adfab0"
)


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=capture)


def scp_base(values: dict[str, str]) -> list[str]:
    return [
        "scp",
        "-i",
        values["SSH_KEY_PATH"],
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
    ]


def status(values: dict[str, str]) -> None:
    run(
        deploy.ssh_base(values)
        + [
            f"cd {REMOTE_ROOT} && docker compose ps && "
            f"docker volume inspect {VOLUME} --format 'volume={{{{.Name}}}} mount={{{{.Mountpoint}}}}' && "
            "df -h / /var/lib/docker"
        ]
    )


def backup(values: dict[str, str], output_dir: Path) -> Path:
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    name = f"technocore-{timestamp}.tgz"
    remote_path = f"{REMOTE_ROOT}/backups/{name}"
    command = (
        f"set -e; cd {REMOTE_ROOT}; install -d -m 0700 backups; "
        "trap 'docker compose start >/dev/null 2>&1 || true' EXIT; "
        "docker compose stop; "
        f"docker run --rm -v {VOLUME}:/data:ro -v {REMOTE_ROOT}/backups:/backup "
        f"{BACKUP_IMAGE} tar -czf /backup/{name} -C /data .; "
        f"chmod 600 {remote_path}; docker compose start; trap - EXIT"
    )
    run(deploy.ssh_base(values) + [command])
    output_dir.mkdir(parents=True, exist_ok=True)
    local_path = output_dir / name
    run(
        scp_base(values)
        + [f"{values['SSH_USER']}@{values['DROPLET_IP']}:{remote_path}", str(local_path)]
    )
    local_path.chmod(0o600)
    return local_path


def restore(values: dict[str, str], archive: Path) -> None:
    if not archive.is_file():
        raise ValueError(f"backup not found: {archive}")
    remote_path = f"{REMOTE_ROOT}/backups/restore.tgz"
    run(
        scp_base(values)
        + [str(archive), f"{values['SSH_USER']}@{values['DROPLET_IP']}:{remote_path}"]
    )
    command = (
        f"set -e; cd {REMOTE_ROOT}; chmod 600 {remote_path}; docker compose down; "
        f"docker run --rm -v {VOLUME}:/data {BACKUP_IMAGE} "
        "sh -c 'rm -rf /data/* /data/.[!.]* /data/..?*'; "
        f"docker run --rm -v {VOLUME}:/data -v {REMOTE_ROOT}/backups:/backup "
        f"{BACKUP_IMAGE} tar -xzf /backup/restore.tgz -C /data; "
        "docker compose up -d --remove-orphans"
    )
    run(deploy.ssh_base(values) + [command])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provision-env",
        type=Path,
        default=Path.home() / ".config" / "technocore-deploy" / "provision.env",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    backup_parser = subparsers.add_parser("backup")
    backup_parser.add_argument("--output-dir", type=Path, default=Path("backups"))
    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("archive", type=Path)
    restore_parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    try:
        values = deploy.load_env(args.provision_env)
        if args.command == "status":
            status(values)
        elif args.command == "backup":
            path = backup(values, args.output_dir)
            print(f"backup: {path}")
        else:
            if not args.yes:
                raise ValueError("restore replaces the live data volume; re-run with --yes")
            restore(values, args.archive)
            print("restore started; run status and the public smoke test")
        return 0
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
