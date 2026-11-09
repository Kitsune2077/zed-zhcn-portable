#!/usr/bin/env python3
"""Limit zed-i18n's config/locales.toml to a keep-list of UI languages.

zed-i18n's universal build ships one runtime locale bundle per locale marked
``enabled = true`` in ``config/locales.toml``, and the in-app language picker
is populated from the same list. This script flips ``enabled`` to ``false``
for every locale outside the keep-list, so a release only bundles (and only
offers) the requested languages.

The source locale is always kept enabled: it has no translation bundle and
serves as the English fallback for every untranslated string.

The rewrite is line-based (no TOML round-trip) so the file's formatting and
comments survive, and it is idempotent.

Usage: limit_i18n_locales.py <locales.toml> [--keep en-US,zh-CN]
"""

import re
import sys
from pathlib import Path

SOURCE_RE = re.compile(r'^\s*source_locale\s*=\s*"([^"]+)"\s*(?:#.*)?$')
ID_RE = re.compile(r'^\s*id\s*=\s*"([^"]+)"\s*(?:#.*)?$')
ENABLED_RE = re.compile(
    r"^(?P<prefix>\s*enabled\s*=\s*)(?P<value>true|false)(?P<suffix>\s*(?:#.*)?)$"
)


def split_eol(line: str) -> tuple[str, str]:
    for eol in ("\r\n", "\n", "\r"):
        if line.endswith(eol):
            return line[: -len(eol)], eol
    return line, ""


def parse_locales(lines: list[str]) -> tuple[str | None, list[dict]]:
    """Return (source_locale, blocks) where each block is
    {"id": str, "enabled_index": int | None}."""
    source = None
    blocks: list[dict] = []
    current: dict | None = None
    for idx, raw in enumerate(lines):
        body, _ = split_eol(raw)
        match = SOURCE_RE.match(body)
        if match:
            source = match.group(1)
            continue
        stripped = body.strip()
        if stripped.startswith("["):
            if current is not None:
                blocks.append(current)
            current = (
                {"id": None, "enabled_index": None}
                if stripped == "[[locale]]"
                else None
            )
            continue
        if current is None:
            continue
        match = ID_RE.match(body)
        if match:
            current["id"] = match.group(1)
            continue
        if ENABLED_RE.match(body):
            current["enabled_index"] = idx
    if current is not None:
        blocks.append(current)
    return source, blocks


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def main() -> int:
    args = sys.argv[1:]
    keep_arg = "en-US,zh-CN"
    if "--keep" in args:
        index = args.index("--keep")
        if index + 1 >= len(args):
            print(
                "usage: limit_i18n_locales.py <locales.toml> [--keep en-US,zh-CN]",
                file=sys.stderr,
            )
            return 2
        keep_arg = args[index + 1]
        del args[index : index + 2]
    if len(args) != 1:
        print(
            f"usage: {sys.argv[0]} <locales.toml> [--keep en-US,zh-CN]",
            file=sys.stderr,
        )
        return 2

    path = Path(args[0])
    if not path.is_file():
        return fail(f"{path} not found - is this a zed-i18n checkout?")

    # Keep the file's exact line endings: read/write with newline="".
    with path.open("r", encoding="utf-8", newline="") as handle:
        lines = handle.readlines()

    source, blocks = parse_locales(lines)
    if source is None:
        return fail("config/locales.toml has no source_locale entry.")
    if not blocks:
        return fail("config/locales.toml has no [[locale]] entries.")
    for block in blocks:
        if not block["id"]:
            return fail("a [[locale]] block has no id.")
        if block["enabled_index"] is None:
            return fail(f"locale {block['id']!r} has no enabled flag.")
    ids = {block["id"] for block in blocks}
    if source not in ids:
        return fail(f"source locale {source!r} is missing from the locale list.")

    keep = [item.strip() for item in keep_arg.split(",") if item.strip()]
    if not keep:
        return fail("--keep needs at least one locale id.")
    unknown = [item for item in keep if item not in ids]
    if unknown:
        return fail(
            f"unknown locale id(s) in --keep: {', '.join(unknown)}; "
            f"available: {', '.join(sorted(ids))}"
        )

    kept = set(keep) | {source}
    changed = 0
    for block in blocks:
        index = block["enabled_index"]
        body, eol = split_eol(lines[index])
        match = ENABLED_RE.match(body)
        desired = "true" if block["id"] in kept else "false"
        if match.group("value") != desired:
            lines[index] = (
                match.group("prefix") + desired + match.group("suffix") + eol
            )
            changed += 1
            print(f"{block['id']}: enabled -> {desired}")

    if changed:
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.writelines(lines)

    enabled = sorted(block["id"] for block in blocks if block["id"] in kept)
    print(
        f"locales.toml: {len(blocks)} locales, enabled {', '.join(enabled)} "
        f"({changed} line(s) changed)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
