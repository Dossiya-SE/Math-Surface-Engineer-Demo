#!/usr/bin/env python3
"""Compare cmark-gfm structure before and after a Markdown-only repair."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def render_xml(path: Path, executable: str) -> str:
    run = subprocess.run(
        [executable, "--to", "xml", "--sourcepos", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return run.stdout


def skeleton(document: str) -> list[tuple[str, tuple[tuple[str, str], ...]]]:
    root = ET.fromstring(document)
    result = []
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        result.append((tag, tuple(sorted(node.attrib.items()))))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--cmark-gfm", default="cmark-gfm")
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()

    executable = shutil.which(args.cmark_gfm)
    if not executable:
        message = f"cmark-gfm executable not found: {args.cmark_gfm}"
        if args.allow_missing:
            print(f"SKIP: {message}")
            return 0
        print(message, file=sys.stderr)
        return 2

    before = skeleton(render_xml(args.before, executable))
    after = skeleton(render_xml(args.after, executable))
    if before != after:
        print("FAIL: cmark-gfm structural skeleton changed", file=sys.stderr)
        for index, pair in enumerate(zip(before, after)):
            if pair[0] != pair[1]:
                print(f"first difference at node {index}: {pair[0]} != {pair[1]}", file=sys.stderr)
                break
        if len(before) != len(after):
            print(f"node counts: {len(before)} != {len(after)}", file=sys.stderr)
        return 1
    print(f"PASS: {len(before)} cmark-gfm nodes preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
