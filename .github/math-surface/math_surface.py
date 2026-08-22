#!/usr/bin/env python3
"""Audit, report, extract, and conservatively repair GitHub mathematics."""

from __future__ import annotations

import argparse
import difflib
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

VERSION = "1.3.0"
DEEP = "*" * 2 + "/"
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdx"}
DEFAULT_INCLUDE = [DEEP + "*.md", DEEP + "*.markdown", DEEP + "*.mdx"]
DEFAULT_EXCLUDE = [DEEP + name + "/**" for name in (".git", "node_modules", "vendor", "dist", "build")]
DEFAULT_ARCHIVAL = [
    DEEP + name + "/**"
    for name in ("archive", "archives", "conversation", "conversation_memory", "memory", "prompts")
] + [DEEP + "*VERBATIM*.md", DEEP + "*SNAPSHOT*.md"]
FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
INLINE_CODE = re.compile(r"(`+)(.*?)\1")
LEGACY = re.compile(r"(?<!\\)\\([\(\)\[\]])")
LEGACY_INLINE = re.compile(r"(?<!\\)\\\(.*?(?<!\\)\\\)")
TEX = re.compile(
    r"\\(?:frac|dfrac|tfrac|sum|prod|int|oint|mathbb|mathbf|mathrm|mathcal|"
    r"operatorname|texttt|text|left|right|begin|end|bigwedge|bigvee|dot|"
    r"ddot|nabla|partial|infty|lambda|mu|sigma|theta|phi|psi|omega|Delta|Sigma|Pi)\b"
)
MOJIBAKE = re.compile(
    r"(?:\u00c3[\u0080-\u00bf]|\u00c2[\u0080-\u00bf]|"
    r"\u00e2(?:\u20ac|[\u0080-\u00bf]).|\u00ef\u00bf\u00bd|\ufffd)"
)
SETEXT_COLLISION = re.compile(r"^\s*(?:=+|-+)\s*$")
RULES = {
    "MSM001": ("legacy-inline-on-github", "Legacy inline delimiter on GitHub Markdown"),
    "MSM002": ("legacy-display-on-github", "Legacy display delimiter on GitHub Markdown"),
    "MSM003": ("raw-tex-outside-math", "TeX command outside a recognized math container"),
    "MSM004": ("unmatched-legacy-delimiter", "Unmatched legacy math delimiter"),
    "MSM005": ("unmatched-display-dollar", "Unmatched double-dollar delimiter"),
    "MSM008": ("probable-mojibake", "Probable character-encoding corruption"),
    "MSM009": ("invalid-utf8", "Document is not valid UTF-8"),
    "MSM010": ("gfm-setext-inside-display", "Display math contains a line parsed as a GFM Setext heading"),
}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    path: str
    line: int
    column: int
    end_line: int
    end_column: int
    severity: str
    confidence: str
    surface: str
    archival: bool
    fixable: bool
    message: str
    snippet: str


@dataclass
class Policy:
    include: list[str]
    exclude: list[str]
    archival: list[str]
    default_surface: str
    overrides: list[dict[str, str]]


def matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or (
        pattern.startswith(DEEP) and fnmatch.fnmatchcase(path, pattern[len(DEEP) :])
    )


def any_match(path: str, patterns: list[str]) -> bool:
    return any(matches(path, pattern) for pattern in patterns)


def load_policy(root: Path, explicit: Path | None = None) -> Policy:
    source = explicit or root / ".math-surface.json"
    if source.exists():
        data = json.loads(source.read_text(encoding="utf-8"))
        if data.get("version") != 1:
            raise ValueError(f"Unsupported policy version: {source}")
        return Policy(
            list(data.get("include", DEFAULT_INCLUDE)),
            list(data.get("exclude", DEFAULT_EXCLUDE)),
            list(data.get("archival", DEFAULT_ARCHIVAL)),
            str(data.get("default_surface", "github-markdown")),
            list(data.get("surface_overrides", [])),
        )
    return Policy(DEFAULT_INCLUDE.copy(), DEFAULT_EXCLUDE.copy(), DEFAULT_ARCHIVAL.copy(), "github-markdown", [])


def surface_for(path: str, policy: Policy) -> str:
    for item in policy.overrides:
        if matches(path, item["glob"]):
            return item["surface"]
    return "mdx" if Path(path).suffix.lower() == ".mdx" else policy.default_surface


def files_for(root: Path, policy: Policy) -> list[Path]:
    root = root.resolve()
    if (root / ".git").exists():
        run = subprocess.run(
            [
                "git", "-C", str(root), "ls-files", "-z",
                "--cached", "--others", "--exclude-standard",
            ],
            check=True,
            capture_output=True,
        )
        candidates = [root / item.decode() for item in run.stdout.split(b"\0") if item]
    else:
        candidates = [item for item in root.rglob("*") if item.is_file()]
    selected = []
    for item in candidates:
        if not item.is_file():
            continue
        relative = item.relative_to(root).as_posix()
        if item.suffix.lower() not in MARKDOWN_SUFFIXES:
            continue
        if not any_match(relative, policy.include) or any_match(relative, policy.exclude):
            continue
        selected.append(item)
    return sorted(selected)


def commit_sha(root: Path) -> str | None:
    if not (root / ".git").exists():
        return None
    run = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    return run.stdout.strip() if run.returncode == 0 else None


def mask_code(line: str) -> str:
    chars = list(line)
    for match in INLINE_CODE.finditer(line):
        chars[match.start() : match.end()] = " " * (match.end() - match.start())
    return "".join(chars)


def mask_supported_math(line: str, display: bool) -> tuple[str, bool]:
    chars, index = list(line), 0
    while index < len(line):
        if line.startswith("$$", index) and (index == 0 or line[index - 1] != "\\"):
            chars[index : index + 2] = "  "
            display = not display
            index += 2
        elif display:
            chars[index] = " "
            index += 1
        elif line[index] == "$" and (index == 0 or line[index - 1] != "\\"):
            end = index + 1
            while end < len(line) and not (line[end] == "$" and line[end - 1] != "\\"):
                end += 1
            if end < len(line):
                chars[index : end + 1] = " " * (end - index + 1)
                index = end + 1
            else:
                index += 1
        else:
            index += 1
    return "".join(chars), display


def finding(rule: str, path: str, line: int, col: int, end_line: int, end_col: int,
            surface: str, archival: bool, snippet: str) -> Finding:
    review = rule in {"MSM003", "MSM008"} or archival or surface == "mdx"
    return Finding(
        rule, path, line, col, end_line, end_col,
        "warning" if review else "error",
        "REVIEW" if review else "HIGH_CONFIDENCE",
        surface, archival, rule in {"MSM001", "MSM002", "MSM010"} and not review,
        RULES[rule][1], snippet.strip()[:240],
    )


def scan_text(text: str, path: str, surface: str, archival: bool) -> list[Finding]:
    if surface not in {"github-markdown", "mdx"}:
        return []
    results: list[Finding] = []
    in_fence, fence_char, fence_len = False, "", 0
    display_open: tuple[int, int, str] | None = None
    dollars_open: tuple[int, int, str] | None = None
    in_dollars = False
    for number, source in enumerate(text.splitlines(), 1):
        for match in MOJIBAKE.finditer(source):
            results.append(finding("MSM008", path, number, match.start() + 1, number,
                                   match.end() + 1, surface, archival, source))
        fence = FENCE.match(source)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence, fence_char, fence_len = True, marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len:
                in_fence, fence_char, fence_len = False, "", 0
            continue
        if in_fence:
            continue
        visible = mask_code(source)
        inline_open: tuple[int, str] | None = None
        display_touched = display_open is not None
        for event in LEGACY.finditer(visible):
            col, token = event.start() + 1, event.group(1)
            if token == "(":
                if inline_open:
                    results.append(finding("MSM004", path, number, col, number, col + 1, surface, archival, source))
                inline_open = (col, source)
            elif token == ")":
                if not inline_open:
                    results.append(finding("MSM004", path, number, col, number, col + 1, surface, archival, source))
                else:
                    results.append(finding("MSM001", path, number, inline_open[0], number, col + 1,
                                           surface, archival, inline_open[1]))
                    inline_open = None
            elif token == "[":
                display_touched = True
                if display_open:
                    results.append(finding("MSM004", path, number, col, number, col + 1, surface, archival, source))
                display_open = (number, col, source)
            elif token == "]":
                display_touched = True
                if not display_open:
                    results.append(finding("MSM004", path, number, col, number, col + 1, surface, archival, source))
                else:
                    results.append(finding("MSM002", path, display_open[0], display_open[1], number, col + 1,
                                           surface, archival, display_open[2]))
                    display_open = None
        if inline_open:
            results.append(finding("MSM004", path, number, inline_open[0], number, inline_open[0] + 1,
                                   surface, archival, inline_open[1]))
        display_before = in_dollars
        for event in re.finditer(r"(?<!\\)\$\$", visible):
            dollars_open = (number, event.start() + 1, source) if dollars_open is None else None
        outside, in_dollars = mask_supported_math(visible, in_dollars)
        if display_before and SETEXT_COLLISION.fullmatch(visible):
            results.append(finding("MSM010", path, number, 1, number, len(source) + 1,
                                   surface, archival, source))
        outside = LEGACY_INLINE.sub(lambda item: " " * len(item.group(0)), outside)
        outside = LEGACY.sub(lambda item: " " * len(item.group(0)), outside)
        if display_touched or display_open:
            continue
        command = TEX.search(outside)
        if command:
            results.append(finding("MSM003", path, number, command.start() + 1, number, command.end() + 1,
                                   surface, archival, source))
    if display_open:
        results.append(finding("MSM004", path, display_open[0], display_open[1], display_open[0],
                               display_open[1] + 1, surface, archival, display_open[2]))
    if dollars_open:
        results.append(finding("MSM005", path, dollars_open[0], dollars_open[1], dollars_open[0],
                               dollars_open[1] + 1, surface, archival, dollars_open[2]))
    return results


def audit(root: Path, policy: Policy) -> tuple[list[Finding], int]:
    root = root.resolve()
    results, scanned = [], 0
    for path in files_for(root, policy):
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            results.append(finding("MSM009", relative, 1, 1, 1, 2,
                                   surface_for(relative, policy),
                                   any_match(relative, policy.archival),
                                   f"UTF-8 decoding failed at byte {error.start}"))
            scanned += 1
            continue
        except OSError:
            continue
        results.extend(scan_text(text, relative, surface_for(relative, policy),
                                 any_match(relative, policy.archival)))
        scanned += 1
    return results, scanned


def report_summary(results: list[Finding], scanned: int, sha: str | None) -> dict[str, Any]:
    return {
        "tool": "engineer-math-surfaces", "version": VERSION, "commit_sha": sha,
        "scanned_files": scanned, "affected_files": len({item.path for item in results}),
        "total_findings": len(results),
        "by_rule": dict(sorted(Counter(item.rule_id for item in results).items())),
        "by_confidence": dict(sorted(Counter(item.confidence for item in results).items())),
    }


def render_json(results: list[Finding], scanned: int, sha: str | None) -> str:
    return json.dumps({"summary": report_summary(results, scanned, sha),
                       "findings": [asdict(item) for item in results]},
                      indent=2, ensure_ascii=False) + "\n"


def render_markdown(results: list[Finding], scanned: int, sha: str | None) -> str:
    tick = chr(96)
    summary = report_summary(results, scanned, sha)
    lines = ["# Mathematics surface audit", "",
             f"- Tool: {tick}engineer-math-surfaces {VERSION}{tick}",
             f"- Commit: {tick}{sha or 'NOT_AVAILABLE'}{tick}",
             f"- Scanned files: {scanned}", f"- Affected files: {summary['affected_files']}",
             f"- Findings: {len(results)}", "",
             "| Rule | File | Location | Confidence | Surface | Meaning |",
             "|---|---|---:|---|---|---|"]
    for item in results:
        lines.append(f"| {item.rule_id} | {tick}{item.path}{tick} | {item.line}:{item.column} | "
                     f"{item.confidence} | {item.surface} | {item.message} |")
    lines += ["", "High-confidence findings violate the declared GitHub Markdown contract. "
              "Review findings require inspection of intent or archival role.", ""]
    return "\n".join(lines)


def render_sarif(results: list[Finding]) -> str:
    used = sorted({item.rule_id for item in results})
    rules = [{"id": key, "name": RULES[key][0],
              "shortDescription": {"text": RULES[key][1]}} for key in used]
    entries = []
    for item in results:
        entries.append({
            "ruleId": item.rule_id, "level": item.severity,
            "message": {"text": item.message},
            "locations": [{"physicalLocation": {
                "artifactLocation": {"uri": item.path},
                "region": {"startLine": item.line, "startColumn": item.column,
                           "endLine": item.end_line, "endColumn": max(item.end_column, item.column + 1)}
            }}],
            "properties": {"confidence": item.confidence, "surface": item.surface,
                           "archival": item.archival, "fixable": item.fixable}
        })
    payload = {"version": "2.1.0", "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
               "runs": [{"tool": {"driver": {"name": "engineer-math-surfaces",
                                               "version": VERSION, "rules": rules}},
                         "results": entries}]}
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def unescaped_dollar(text: str) -> bool:
    return any(char == "$" and (index == 0 or text[index - 1] != "\\")
               for index, char in enumerate(text))


def is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def inline_dollar_fragments(text: str) -> list[str]:
    """Extract non-display dollar spans without crossing adjacent expressions."""
    fragments: list[str] = []
    index = 0
    while index < len(text):
        if (text[index] != "$" or is_escaped(text, index)
                or (index > 0 and text[index - 1] == "$")
                or (index + 1 < len(text) and text[index + 1] == "$")):
            index += 1
            continue
        end = index + 1
        while end < len(text):
            if (text[end] == "$" and not is_escaped(text, end)
                    and (end + 1 >= len(text) or text[end + 1] != "$")):
                body = text[index + 1:end]
                if body.strip():
                    fragments.append(body)
                index = end + 1
                break
            end += 1
        else:
            break
    return fragments


def legacy_semantic_hashes(text: str) -> list[dict[str, Any]]:
    """Hash TeX bodies before delimiter conversion without interpreting TeX."""
    records: list[dict[str, Any]] = []
    offset, in_fence, fence_char, fence_len = 0, False, "", 0
    display_open: tuple[int, int, int] | None = None
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        plain = line.rstrip("\r\n")
        fence = FENCE.match(plain)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence, fence_char, fence_len = True, marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len:
                in_fence, fence_char, fence_len = False, "", 0
            offset += len(line)
            continue
        if in_fence:
            offset += len(line)
            continue
        inline_open: tuple[int, int] | None = None
        for event in LEGACY.finditer(mask_code(plain)):
            absolute, token = offset + event.start(), event.group(1)
            if token == "(":
                inline_open = (absolute, number)
            elif token == ")" and inline_open is not None:
                body = text[inline_open[0] + 2:absolute]
                records.append({
                    "line": inline_open[1], "display": False,
                    "tex_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                })
                inline_open = None
            elif token == "[":
                display_open = (absolute, number, event.start() + 1)
            elif token == "]" and display_open is not None:
                body = text[display_open[0] + 2:absolute]
                records.append({
                    "line": display_open[1], "display": True,
                    "tex_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                })
                display_open = None
        offset += len(line)
    return records


def rewrite_dollar_collisions(text: str) -> tuple[str, list[str]]:
    """Use a math fence when GFM would parse a display body as Markdown structure."""
    lines = text.splitlines(keepends=True)
    skipped: list[str] = []
    in_fence, fence_char, fence_len = False, "", 0
    display_open: int | None = None
    for index, line in enumerate(lines):
        plain = line.rstrip("\r\n")
        fence = FENCE.match(plain)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence, fence_char, fence_len = True, marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len:
                in_fence, fence_char, fence_len = False, "", 0
            continue
        if in_fence or plain.strip() != "$$":
            continue
        if display_open is None:
            display_open = index
            continue
        body_lines = lines[display_open + 1:index]
        if any(SETEXT_COLLISION.fullmatch(item.rstrip("\r\n")) for item in body_lines):
            if any("```" in item for item in body_lines):
                skipped.append(f"lines {display_open + 1}-{index + 1}: math-fence collision")
            else:
                opening_newline = lines[display_open][len(lines[display_open].rstrip("\r\n")):]
                closing_newline = line[len(line.rstrip("\r\n")):]
                opening_plain = lines[display_open].rstrip("\r\n")
                indent = opening_plain[:len(opening_plain) - len(opening_plain.lstrip())]
                lines[display_open] = f"{indent}```math{opening_newline}"
                lines[index] = f"{indent}```{closing_newline}"
        display_open = None
    return "".join(lines), skipped


def dollar_collision_bodies(text: str) -> list[dict[str, Any]]:
    """Return exact TeX bodies from GFM-collision-prone dollar displays."""
    lines = text.splitlines(keepends=True)
    records: list[dict[str, Any]] = []
    in_fence, fence_char, fence_len = False, "", 0
    display_open: int | None = None
    for index, line in enumerate(lines):
        plain = line.rstrip("\r\n")
        fence = FENCE.match(plain)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence, fence_char, fence_len = True, marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len:
                in_fence, fence_char, fence_len = False, "", 0
            continue
        if in_fence or plain.strip() != "$$":
            continue
        if display_open is None:
            display_open = index
            continue
        body_lines = lines[display_open + 1:index]
        if any(SETEXT_COLLISION.fullmatch(item.rstrip("\r\n")) for item in body_lines):
            body = "".join(body_lines)
            records.append({
                "line": display_open + 1,
                "body": body,
                "tex_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            })
        display_open = None
    return records


def math_fence_bodies(text: str) -> list[str]:
    """Return exact bodies of fenced GitHub math containers."""
    lines = text.splitlines(keepends=True)
    bodies: list[str] = []
    index = 0
    while index < len(lines):
        plain = lines[index].rstrip("\r\n")
        fence = FENCE.match(plain)
        language = fence.group(2).strip().split(maxsplit=1)[0:1] if fence else []
        if not fence or [item.lower() for item in language] != ["math"]:
            index += 1
            continue
        marker = fence.group(1)
        close = index + 1
        while close < len(lines):
            candidate = FENCE.match(lines[close].rstrip("\r\n"))
            if (candidate and candidate.group(1)[0] == marker[0]
                    and len(candidate.group(1)) >= len(marker)):
                bodies.append("".join(lines[index + 1:close]))
                index = close + 1
                break
            close += 1
        else:
            index += 1
    return bodies


def collision_semantic_records(original: str, revised: str) -> list[dict[str, Any]]:
    """Verify every MSM010 body survives its container conversion byte-for-byte."""
    available = Counter(
        hashlib.sha256(body.encode("utf-8")).hexdigest()
        for body in math_fence_bodies(revised)
    )
    records: list[dict[str, Any]] = []
    for item in dollar_collision_bodies(original):
        digest = item["tex_sha256"]
        verified = available[digest] > 0
        if verified:
            available[digest] -= 1
        records.append({
            "line": item["line"],
            "display": True,
            "rule_id": "MSM010",
            "before_tex_sha256": digest,
            "after_tex_sha256": digest if verified else None,
            "byte_identical": verified,
        })
    return records


def rewrite(text: str) -> tuple[str, list[str]]:
    replacements, skipped = [], []
    offset, in_fence, fence_char, fence_len = 0, False, "", 0
    display_open: tuple[int, int] | None = None
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        plain = line.rstrip("\r\n")
        fence = FENCE.match(plain)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence, fence_char, fence_len = True, marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len:
                in_fence, fence_char, fence_len = False, "", 0
            offset += len(line)
            continue
        if in_fence:
            offset += len(line)
            continue
        inline_open = None
        for event in LEGACY.finditer(mask_code(plain)):
            absolute, token = offset + event.start(), event.group(1)
            if token == "(":
                inline_open = absolute
            elif token == ")" and inline_open is not None:
                body = text[inline_open + 2 : absolute]
                if body.strip() and not unescaped_dollar(body):
                    replacements += [(inline_open, inline_open + 2, "$"), (absolute, absolute + 2, "$")]
                else:
                    skipped.append(f"line {number}: ambiguous inline expression")
                inline_open = None
            elif token == "[":
                display_open = (absolute, number)
            elif token == "]" and display_open:
                body = text[display_open[0] + 2 : absolute]
                if body.strip() and not unescaped_dollar(body):
                    replacements += [(display_open[0], display_open[0] + 2, "$$"),
                                     (absolute, absolute + 2, "$$")]
                else:
                    skipped.append(f"lines {display_open[1]}-{number}: ambiguous display expression")
                display_open = None
        offset += len(line)
    if display_open:
        skipped.append(f"line {display_open[1]}: unmatched display delimiter")
    output = text
    for start, end, replacement in sorted(replacements, reverse=True):
        output = output[:start] + replacement + output[end:]
    output, collision_skipped = rewrite_dollar_collisions(output)
    return output, skipped + collision_skipped


def fix(root: Path, policy: Policy, apply: bool, allow_archival: bool,
        allow_mdx: bool, ledger_path: Path | None) -> int:
    root = root.resolve()
    ledger: dict[str, Any] = {"tool": "engineer-math-surfaces", "version": VERSION,
                              "commit_sha": commit_sha(root), "applied": apply, "files": []}
    for path in files_for(root, policy):
        relative = path.relative_to(root).as_posix()
        surface, archival = surface_for(relative, policy), any_match(relative, policy.archival)
        if surface not in {"github-markdown", "mdx"} or (archival and not allow_archival):
            continue
        if surface == "mdx" and not allow_mdx:
            continue
        original = path.read_text(encoding="utf-8")
        revised, skipped = rewrite(original)
        if revised == original:
            continue
        collision_records = collision_semantic_records(original, revised)
        if any(not item["byte_identical"] for item in collision_records):
            raise RuntimeError(f"MSM010 semantic-preservation failure: {relative}")
        sys.stdout.write("".join(difflib.unified_diff(
            original.splitlines(keepends=True), revised.splitlines(keepends=True),
            fromfile=f"a/{relative}", tofile=f"b/{relative}")))
        ledger["files"].append({
            "path": relative, "surface": surface, "archival": archival,
            "before_sha256": hashlib.sha256(original.encode()).hexdigest(),
            "after_sha256": hashlib.sha256(revised.encode()).hexdigest(),
            "preserved_tex_bodies": legacy_semantic_hashes(original),
            "preserved_collision_bodies": collision_records,
            "skipped": skipped,
        })
        if apply:
            path.write_text(revised, encoding="utf-8")
    ledger["changed_files"] = len(ledger["files"])
    if ledger_path:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    return 0


def extract(root: Path, policy: Policy) -> list[dict[str, Any]]:
    root = root.resolve()
    records = []
    for path in files_for(root, policy):
        relative = path.relative_to(root).as_posix()
        if surface_for(relative, policy) not in {"github-markdown", "mdx"}:
            continue
        in_fence, math_fence, marker_char, marker_len = False, False, "", 0
        math_lines, math_start = [], 0
        display_lines, display_start = [], 0
        in_display = False
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            fence = FENCE.match(line)
            if fence:
                marker, language = fence.group(1), fence.group(2).strip().lower()
                if not in_fence:
                    in_fence, math_fence = True, language == "math"
                    marker_char, marker_len, math_lines, math_start = marker[0], len(marker), [], number + 1
                elif marker[0] == marker_char and len(marker) >= marker_len:
                    if math_fence:
                        records.append({"path": relative, "line": math_start, "display": True,
                                        "syntax": "math-fence", "tex": "\n".join(math_lines)})
                    in_fence, math_fence = False, False
                continue
            if in_fence:
                if math_fence:
                    math_lines.append(line)
                continue
            visible = mask_code(line)
            if in_display:
                if "$$" in visible:
                    head, _sep, tail = visible.partition("$$")
                    display_lines.append(head)
                    records.append({"path": relative, "line": display_start, "display": True,
                                    "syntax": "double-dollar", "tex": "\n".join(display_lines).strip()})
                    in_display, display_lines, visible = False, [], tail
                else:
                    display_lines.append(visible)
                    continue
            if "$$" in visible:
                head, _sep, tail = visible.partition("$$")
                if "$$" in tail:
                    tex, _sep2, rest = tail.partition("$$")
                    records.append({"path": relative, "line": number, "display": True,
                                    "syntax": "double-dollar", "tex": tex.strip()})
                    visible = head + rest
                else:
                    in_display, display_start, display_lines, visible = True, number, [tail], head
            for body in inline_dollar_fragments(visible):
                records.append({"path": relative, "line": number, "display": False,
                                "syntax": "dollar", "tex": body})
    return records


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    audit_cmd = commands.add_parser("audit")
    audit_cmd.add_argument("root", type=Path)
    audit_cmd.add_argument("--policy", type=Path)
    audit_cmd.add_argument("--format", choices=["json", "markdown", "sarif"], default="json")
    audit_cmd.add_argument("--output", type=Path)
    audit_cmd.add_argument("--fail-on", choices=["error", "warning", "none"], default="error")
    fix_cmd = commands.add_parser("fix")
    fix_cmd.add_argument("root", type=Path)
    fix_cmd.add_argument("--policy", type=Path)
    fix_cmd.add_argument("--apply", action="store_true")
    fix_cmd.add_argument("--allow-archival", action="store_true")
    fix_cmd.add_argument("--allow-mdx", action="store_true")
    fix_cmd.add_argument("--ledger", type=Path)
    extract_cmd = commands.add_parser("extract")
    extract_cmd.add_argument("root", type=Path)
    extract_cmd.add_argument("--policy", type=Path)
    extract_cmd.add_argument("--output", type=Path, required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    repository = args.root.resolve()
    policy = load_policy(repository, args.policy)
    if args.command == "fix":
        return fix(repository, policy, args.apply, args.allow_archival, args.allow_mdx, args.ledger)
    if args.command == "extract":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(extract(repository, policy), indent=2) + "\n", encoding="utf-8")
        return 0
    results, scanned = audit(repository, policy)
    sha = commit_sha(repository)
    content = {"json": render_json, "markdown": render_markdown,
               "sarif": lambda items, _count, _sha: render_sarif(items)}[args.format](results, scanned, sha)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    else:
        sys.stdout.write(content)
    if args.fail_on == "none":
        return 0
    if args.fail_on == "warning":
        return int(bool(results))
    return int(any(item.severity == "error" for item in results))


if __name__ == "__main__":
    raise SystemExit(main())
