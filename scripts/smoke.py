#!/usr/bin/env python3
"""Exercise public Technocore protocol behavior and prove origin port isolation."""

from __future__ import annotations

import argparse
import json
import secrets
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

def request(url: str, expected: tuple[int, ...] = (200,)) -> tuple[int, bytes, object]:
    separator = "&" if "?" in url else "?"
    outgoing = urllib.request.Request(
        f"{url}{separator}n={time.time_ns()}",
        headers={"User-Agent": "technocore-deploy-smoke/0.2"},
    )
    try:
        response = urllib.request.urlopen(outgoing, timeout=20)
    except urllib.error.HTTPError as error:
        status, body, headers = error.code, error.read(), error.headers
    else:
        with response:
            status, body, headers = response.status, response.read(), response.headers
    if status not in expected:
        raise RuntimeError(f"GET {url} returned HTTP {status}: {body[:200]!r}")
    return status, body, headers


def get(url: str) -> bytes:
    return request(url)[1]


def version_tuple(value: str) -> tuple[int, int, int]:
    try:
        parts = tuple(int(part) for part in value.split("."))
    except ValueError as error:
        raise RuntimeError(f"invalid release version: {value!r}") from error
    if len(parts) != 3:
        raise RuntimeError(f"invalid release version: {value!r}")
    return parts


def validate_manifest(manifest: dict, base: str, expected_version: str) -> None:
    if manifest.get("name") != "technocore-chat" or manifest.get("url") != base:
        raise RuntimeError("agent manifest name or public URL is wrong")
    if manifest.get("version") != expected_version:
        raise RuntimeError(
            f"expected Technocore {expected_version}, got {manifest.get('version')!r}"
        )


def validate_config(config: dict) -> int:
    settings = config.get("settings")
    withheld = config.get("withheld")
    if config.get("env_prefix") != "CHAT_" or not isinstance(settings, dict):
        raise RuntimeError("unexpected /config shape")
    if not isinstance(withheld, dict) or not {"CHAT_ROOT", "CHAT_CLIENT_IP_HEADER"} <= set(
        withheld
    ):
        raise RuntimeError("/config does not classify sensitive settings as withheld")
    if settings.get("dupe_filter_seconds", 0) <= 0:
        raise RuntimeError("duplicate filter is disabled")
    copies = settings.get("dupe_max_copies")
    if not isinstance(copies, int) or not 1 <= copies <= 10:
        raise RuntimeError(f"unsafe duplicate-filter smoke count: {copies!r}")
    return copies


def validate_export(body: bytes, headers: object, room_data: dict, text: str) -> None:
    records = [json.loads(line) for line in body.splitlines()]
    if not any(record.get("text") == text for record in records):
        raise RuntimeError("room export did not contain the smoke message")
    generation = str(room_data.get("generation"))
    if getattr(headers, "get")("X-Room-Generation") != generation:
        raise RuntimeError("export generation did not match room view")


def assert_origin_closed(host: str, port: int = 8080) -> None:
    try:
        with socket.create_connection((host, port), timeout=5):
            pass
    except (ConnectionRefusedError, TimeoutError, OSError):
        return
    raise RuntimeError(f"origin {host}:{port} is publicly reachable")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--origin-ip", required=True)
    parser.add_argument("--origin-port", type=int, default=8080)
    parser.add_argument("--expected-version", default="0.11.4")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    try:
        health = get(f"{base}/healthz").decode().strip()
        if health != "ok":
            raise RuntimeError(f"unexpected health body: {health!r}")

        manual = get(f"{base}/llms.txt").decode()
        if "HTTP-native chat and notes" not in manual:
            raise RuntimeError("manual did not identify the Technocore protocol")

        manifest = json.loads(get(f"{base}/.well-known/agent.json"))
        validate_manifest(manifest, base, args.expected_version)
        release = version_tuple(args.expected_version)

        dupe_max_copies = 0
        if release >= (0, 9, 7):
            config = json.loads(get(f"{base}/config"))
            dupe_max_copies = validate_config(config)
        openapi = json.loads(get(f"{base}/openapi.json"))
        if openapi.get("openapi") != "3.1.0":
            raise RuntimeError("unexpected OpenAPI version")

        marker = secrets.token_hex(8)
        room = f"e-deploy-smoke-{marker}"
        text = f"deployment-smoke-{marker} SELECT * FROM agents <script>not-executed</script>"
        write_url = f"{base}/r/{room}/say/deploy-smoke/{urllib.parse.quote(text, safe='')}"
        get(write_url)
        room_data = json.loads(get(f"{base}/r/{room}?format=json&limit=10"))
        if not any(message.get("text") == text for message in room_data.get("messages", [])):
            raise RuntimeError("public write did not round-trip")
        if release >= (0, 11, 0):
            _, exported, export_headers = request(f"{base}/r/{room}/export")
            validate_export(exported, export_headers, room_data, text)

        if release >= (0, 10, 0):
            duplicate_room = f"e-deploy-dupe-{marker}"
            duplicate_text = f"deployment duplicate-filter proof {marker}"
            duplicate_url = (
                f"{base}/r/{duplicate_room}/say/deploy-smoke/"
                f"{urllib.parse.quote(duplicate_text, safe='')}"
            )
            for _ in range(dupe_max_copies):
                request(duplicate_url)
            request(duplicate_url, expected=(422,))
        assert_origin_closed(args.origin_ip, args.origin_port)
        print(f"protocol {args.expected_version}: ok ({base})")
        if release >= (0, 9, 7):
            print(f"config: ok; duplicate threshold {dupe_max_copies}")
        if release >= (0, 10, 0):
            print(f"duplicate filter: ok ({dupe_max_copies} copies, then 422)")
        if release >= (0, 11, 0):
            print(f"export + generation: ok ({room})")
        print(f"ephemeral write/read: ok ({room})")
        print(f"origin isolation: ok ({args.origin_ip}:{args.origin_port} closed)")
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
