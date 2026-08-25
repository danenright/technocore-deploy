#!/usr/bin/env python3
"""Exercise public Technocore protocol behavior and prove origin port isolation."""

from __future__ import annotations

import argparse
import json
import secrets
import socket
import sys
import time
import urllib.parse
import urllib.request


def get(url: str) -> bytes:
    separator = "&" if "?" in url else "?"
    request = urllib.request.Request(
        f"{url}{separator}n={time.time_ns()}",
        headers={"User-Agent": "technocore-deploy-smoke/0.1"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"GET {url} returned HTTP {response.status}")
        return response.read()


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
        if manifest.get("name") != "technocore-chat" or manifest.get("url") != base:
            raise RuntimeError("agent manifest name or public URL is wrong")

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

        assert_origin_closed(args.origin_ip)
        print(f"public protocol: ok ({base})")
        print(f"ephemeral write/read: ok ({room})")
        print(f"origin isolation: ok ({args.origin_ip}:8080 closed)")
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
