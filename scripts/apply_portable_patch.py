#!/usr/bin/env python3
"""Apply the portable-data-dir patch to a checked-out zed source tree
(official zed-industries/zed or any fork, e.g. zed-ZH_CN).

This is an insertion-only, anchor-based patch (deliberately not a unified
diff, so it survives unrelated upstream changes to main.rs):

  * right before ``init_paths()`` in ``crates/zed/src/main.rs`` it inserts a
    block that, when the executable's folder is writable, redirects ALL user
    data (config / extensions / databases / logs) into a ``data`` folder next
    to the executable, and seeds a ``settings.json`` on first run;
  * if the folder is not writable (e.g. the exe was dropped into Program
    Files) the block does nothing and Zed falls back to its platform default
    directories.

The seeded settings default to a Chinese, no-auto-update config (suited to
runtime-i18n forks like zed-ZH_CN). Pass ``--seed-settings <file>`` to embed
a different JSON file - e.g. the official-source build (zed-i18n pipeline)
bakes translations into the binary and seeds no ``ui_language`` key.

The script is idempotent and fails loudly (non-zero exit) when upstream code
drifts, so CI never silently produces a non-portable build.

Usage: apply_portable_patch.py <zed-source-root> [--seed-settings <json-file>]
"""

import sys
from pathlib import Path

MARKER = "zed-zhcn-portable"

# Anchors tried in order. The block is inserted directly above the first
# matching line, reusing that line's indentation.
ANCHORS = [
    "let file_errors = init_paths();",
    "init_paths();",
]

# Default first-run settings: Chinese UI + no auto-update + no telemetry.
# Embedded into the Rust source as a raw string literal (real newlines kept).
DEFAULT_SEED_SETTINGS = """\
{
  "ui_language": "zh-CN",
  "auto_update": false,
  "telemetry": { "diagnostics": false, "metrics": false }
}
"""

# Note: set_custom_data_dir takes &str (verified against zed v1.27.0, both
# official and zed-ZH_CN), creates the directory itself and panics on
# failure - hence the create_dir_all() probe above the call, which doubles
# as the "is this location writable" check that decides whether portable
# mode activates at all. __SEED_SETTINGS_LITERAL__ is replaced with a raw
# string literal holding the seed settings JSON.
RUST_BLOCK = '''\
if args.user_data_dir.is_none() {
    if let Some(exe_dir) = std::env::current_exe()
        .ok()
        .and_then(|exe| exe.parent().map(|dir| dir.to_path_buf()))
    {
        let data_dir = exe_dir.join("data");
        if std::fs::create_dir_all(&data_dir).is_ok() {
            paths::set_custom_data_dir(&data_dir.to_string_lossy());
            let config_dir = data_dir.join("config");
            let _ = std::fs::create_dir_all(&config_dir);
            let settings_path = config_dir.join("settings.json");
            if !settings_path.exists() {
                let _ = std::fs::write(
                    &settings_path,
                    __SEED_SETTINGS_LITERAL__
                );
            }
        }
    }
}
'''


def seed_settings_literal(seed_path: str | None) -> str:
    """Return a Rust raw string literal with the seed settings JSON."""
    if seed_path is None:
        text = DEFAULT_SEED_SETTINGS
    else:
        file = Path(seed_path)
        if not file.is_file():
            raise SystemExit(f"error: seed settings file not found: {seed_path}")
        text = file.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
    if '"#' in text:
        raise SystemExit(
            'error: seed settings contain the Rust raw-string terminator `"#`; '
            f"cannot embed {seed_path or 'defaults'}"
        )
    return 'r#"' + text + '"#'


def fail(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    print(
        "error: upstream zed code drifted; update ANCHORS / RUST_BLOCK in "
        "scripts/apply_portable_patch.py and re-run.",
        file=sys.stderr,
    )
    return 1


def main() -> int:
    args = sys.argv[1:]
    seed_path = None
    if "--seed-settings" in args:
        idx = args.index("--seed-settings")
        if idx + 1 >= len(args):
            print("usage: apply_portable_patch.py <zed-source-root> "
                  "[--seed-settings <json-file>]", file=sys.stderr)
            return 2
        seed_path = args[idx + 1]
        del args[idx:idx + 2]
    if len(args) != 1:
        print(f"usage: {sys.argv[0]} <zed-source-root> [--seed-settings <json-file>]",
              file=sys.stderr)
        return 2
    root = Path(args[0])

    main_rs = root / "crates" / "zed" / "src" / "main.rs"
    paths_rs = root / "crates" / "paths" / "src" / "paths.rs"
    for path in (main_rs, paths_rs):
        if not path.is_file():
            return fail(f"{path} not found - is this a zed source checkout?")

    paths_src = paths_rs.read_text(encoding="utf-8")
    if "pub fn set_custom_data_dir" not in paths_src:
        return fail("paths::set_custom_data_dir no longer exists upstream.")

    src = main_rs.read_text(encoding="utf-8")
    if MARKER in src:
        print("portable patch: already applied, nothing to do")
        return 0

    if "args.user_data_dir" not in src:
        return fail("'args.user_data_dir' no longer referenced in main.rs.")

    anchor_idx = None
    indent = ""
    for candidate in ANCHORS:
        for i, line in enumerate(src.splitlines()):
            if candidate in line:
                anchor_idx = i
                indent = line[: len(line) - len(line.lstrip())]
                break
        if anchor_idx is not None:
            break
    if anchor_idx is None:
        return fail("no init_paths() anchor found in main.rs.")

    block = RUST_BLOCK.replace(
        "__SEED_SETTINGS_LITERAL__", seed_settings_literal(seed_path)
    )

    header = "\n".join(
        [
            f"{indent}// {MARKER}: keep all user data in a `data` folder next",
            f"{indent}// to the executable when writable, and seed a",
            f"{indent}// no-auto-update settings.json on first run.",
        ]
    )
    # Indent every line to match the anchor, EXCEPT lines inside the seed
    # settings raw string literal (they are the literal's content - indenting
    # them would just add noise whitespace to the generated settings.json).
    indented = []
    in_raw = False
    for line in block.splitlines():
        if in_raw:
            indented.append(line)
            if '"#' in line:
                in_raw = False
        else:
            indented.append(indent + line if line.strip() else "")
            if 'r#"' in line and '"#' not in line.split('r#"', 1)[1]:
                in_raw = True
    body = "\n".join(indented)

    lines = src.splitlines(keepends=True)
    inserted = [line + "\n" for line in f"{header}\n{body}".split("\n")]
    prev = lines[anchor_idx - 1] if anchor_idx > 0 else "\n"
    prefix = [] if prev.strip() == "" else ["\n"]
    patched = lines[:anchor_idx] + prefix + inserted + ["\n"] + lines[anchor_idx:]
    main_rs.write_text("".join(patched), encoding="utf-8", newline="")

    print(f"portable patch: inserted {len(inserted)} lines above line {anchor_idx + 1}:")
    for line in inserted:
        print(f"  + {line.rstrip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
