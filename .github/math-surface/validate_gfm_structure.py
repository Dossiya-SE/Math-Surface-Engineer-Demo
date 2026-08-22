#!/usr/bin/env python3
"""Compare cmark-gfm structure before and after a Markdown-only repair."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
GFM_EXTENSIONS = ("table", "strikethrough", "autolink", "tagfilter", "tasklist")


def normalize_math_blocks(text: str) -> str:
    """Replace complete approved display containers with one neutral block."""
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    index = 0
    while index < len(lines):
        plain = lines[index].rstrip("\r\n")
        fence = FENCE.match(plain)
        if fence:
            indent, marker, info = fence.groups()
            close = index + 1
            while close < len(lines):
                candidate = FENCE.match(lines[close].rstrip("\r\n"))
                if (candidate and candidate.group(2)[0] == marker[0]
                        and len(candidate.group(2)) >= len(marker)):
                    break
                close += 1
            if close >= len(lines):
                output.extend(lines[index:])
                break
            language = info.strip().split(maxsplit=1)[0].lower() if info.strip() else ""
            if language == "math":
                newline = lines[index][len(plain):] or "\n"
                output.append(f"{indent}MATH_BLOCK{newline}")
            else:
                output.extend(lines[index:close + 1])
            index = close + 1
            continue
        token = plain.strip()
        if token in {r"\[", "$$"}:
            closing = r"\]" if token == r"\[" else "$$"
            close = index + 1
            while close < len(lines) and lines[close].rstrip("\r\n").strip() != closing:
                close += 1
            if close < len(lines):
                indent = plain[:len(plain) - len(plain.lstrip())]
                newline = lines[index][len(plain):] or "\n"
                output.append(f"{indent}MATH_BLOCK{newline}")
                index = close + 1
                continue
        output.append(lines[index])
        index += 1
    return "".join(output)


def render_xml(text: str, executable: str) -> str:
    command = [executable, "--to", "xml"]
    for extension in GFM_EXTENSIONS:
        command.extend(["--extension", extension])
    run = subprocess.run(
        command,
        check=True,
        capture_output=True,
        input=text,
        text=True,
    )
    return run.stdout


def skeleton(document: str) -> list[tuple[str, tuple[tuple[str, str], ...]]]:
    root = ET.fromstring(document)
    result = []
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        attributes = tuple(sorted(
            (key, value) for key, value in node.attrib.items() if key != "sourcepos"
        ))
        result.append((tag, attributes))
    return result


def structure_for_text(text: str, executable: str) -> list[tuple[str, tuple[tuple[str, str], ...]]]:
    return skeleton(render_xml(normalize_math_blocks(text), executable))


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

    before_text = args.before.read_text(encoding="utf-8")
    after_text = args.after.read_text(encoding="utf-8")
    before = structure_for_text(before_text, executable)
    after = structure_for_text(after_text, executable)
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
