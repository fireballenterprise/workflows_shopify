#!/usr/bin/env python3
"""Live-theme drift guard for a prd (live) `shopify theme push` — stdlib only.

Compares the live theme (pulled with `shopify theme pull --path LIVE`) with the theme files at the
previously deployed release tag (extracted to BASE) and with the checkout being pushed (HEAD). A
live file matching neither is a GUI edit made in the Shopify admin that git doesn't have: exit 1
with the file list, unless --overwrite-live-edits.

Also decides whether the push may delete remote-only files: only when every live file missing from
the checkout (HEAD) existed at the release tag, i.e. was deleted in git on purpose. Writes
`flags=` (deletes allowed) or `flags=--nodelete` to --output (e.g. $GITHUB_OUTPUT).

Mirror of fireball_orchestrator's modules/shopify/theme_guard.py (same rules; that one reads the
live theme via the Admin API). Keep the two in step.

    drift_guard.py --live DIR --base DIR --head DIR [--baseline TAG] [--ignore 'glob,glob']
                   [--overwrite-live-edits] [--output FILE]
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any

THEME_DIRS = ("assets", "blocks", "config", "layout", "locales", "sections", "snippets", "templates")
_LEADING_BLOCK_COMMENT = re.compile(r"^\s*/\*.*?\*/", re.DOTALL)


def theme_files(root: Path) -> dict[str, Path]:
    """Theme files under root, keyed by their theme path (e.g. `config/settings_data.json`)."""
    files: dict[str, Path] = {}
    for top in THEME_DIRS:
        base = root / top
        if base.is_dir():
            for path in base.rglob("*"):
                if path.is_file():
                    files[path.relative_to(root).as_posix()] = path
    return files


def _parse_json(data: bytes) -> Any:
    return json.loads(_LEADING_BLOCK_COMMENT.sub("", data.decode("utf-8"), count=1))


def _drop_pruned_app_settings(git: Any, live: Any) -> Any:
    """Shopify drops app-block settings the app's schema no longer declares; ignore exactly those."""
    if isinstance(git, list) and isinstance(live, list) and len(git) == len(live):
        return [_drop_pruned_app_settings(g, lv) for g, lv in zip(git, live, strict=True)]
    if not (isinstance(git, dict) and isinstance(live, dict)):
        return git
    result = {key: _drop_pruned_app_settings(value, live[key]) if key in live else value for key, value in git.items()}
    is_app_block = str(git.get("type", "")).startswith("shopify://apps/") and git.get("type") == live.get("type")
    if is_app_block and isinstance(git.get("settings"), dict) and isinstance(live.get("settings"), dict):
        result["settings"] = {key: value for key, value in result["settings"].items() if key in live["settings"]}
    return result


def same_content(filename: str, live: bytes, git: bytes) -> bool:
    """Byte-equal, JSON-equal (Shopify re-serializes JSON + adds a comment header), or equal modulo EOL."""
    if live == git:
        return True
    if filename.endswith(".json"):
        try:
            live_json, git_json = _parse_json(live), _parse_json(git)
        except ValueError:
            return False
        return live_json == _drop_pruned_app_settings(git_json, live_json)
    return live.replace(b"\r\n", b"\n").rstrip() == git.replace(b"\r\n", b"\n").rstrip()


def main(argv: list[str] | None = None) -> int:
    """Run the guard; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", type=Path, required=True, help="dir the live theme was pulled into")
    parser.add_argument("--base", type=Path, required=True, help="theme files at the last release tag")
    parser.add_argument("--head", type=Path, required=True, help="the checkout being pushed")
    parser.add_argument("--baseline", default="", help="release tag name, for messages")
    parser.add_argument("--ignore", default="", help="comma/newline-separated globs Shopify/apps rewrite")
    parser.add_argument("--overwrite-live-edits", action="store_true")
    parser.add_argument("--output", type=Path, help="append `flags=<push flags>` here (e.g. $GITHUB_OUTPUT)")
    args = parser.parse_args(argv)

    patterns = [p.strip() for p in re.split(r"[,\n]", args.ignore) if p.strip()]
    ignored = lambda name: any(fnmatch.fnmatchcase(name, p) for p in patterns)  # noqa: E731
    live, base, head = theme_files(args.live), theme_files(args.base), theme_files(args.head)

    def is_gui_edit(name: str) -> bool:
        """A live file matching neither the release nor the checkout (so a pulled + committed
        live edit clears the guard)."""
        data = live[name].read_bytes()
        known = [src[name].read_bytes() for src in (base, head) if name in src]
        return not any(same_content(name, data, other) for other in known)

    modified = sorted(n for n in live if (n in base or n in head) and not ignored(n) and is_gui_edit(n))
    added_live = sorted(n for n in live if n not in base and n not in head and not ignored(n))
    deleted_live = sorted(n for n in base if n not in live and n in head and not ignored(n))
    drifted = modified + added_live + deleted_live

    if drifted:
        print(f"::group::Live theme differs from release {args.baseline} ({len(drifted)} file(s))")
        for label, names in (
            ("changed in admin", modified),
            ("added in admin", added_live),
            ("deleted in admin", deleted_live),
        ):
            for name in names:
                print(f"  {label:<17} {name}")
        print("::endgroup::")
        files = ", ".join(drifted)
        if not args.overwrite_live_edits:
            print(
                f"::error::Live theme has GUI edits not in git ({files}). Pull them first — locally: "
                "`invoke shopify.pull --site=<site> --env=prd`, commit to development, then release again. "
                "Or re-run with overwrite_live_edits: true to discard them (the pulled live theme is still "
                "uploaded as the live-theme-backup artifact)."
            )
            return 1
        print(f"::warning::overwrite_live_edits: pushing over live GUI edits ({files}).")
    else:
        print(f"Live theme matches release {args.baseline} — no GUI edits.")

    remote_only = sorted(n for n in live if n not in head)
    unexpected = [n for n in remote_only if n not in base]
    for name in remote_only:
        print(f"  remote-only {'(deleted in git — will delete)' if name in base else '(not in git — kept)':<30} {name}")
    if unexpected and len(unexpected) != len(remote_only):
        print("::warning::Keeping files deleted in git on purpose too (--nodelete covers the whole push).")
    flags = "--nodelete" if unexpected else ""
    print(f"push flags: {flags or '(none)'}")
    if args.output:
        with args.output.open("a", encoding="utf-8") as out:
            out.write(f"flags={flags}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
