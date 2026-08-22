#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import math_surface as subject
import validate_gfm_structure as structure


class ScanTests(unittest.TestCase):
    def test_detects_balanced_legacy_delimiters(self):
        text = "Inline \\(x+y\\).\n\n\\[\nA=B\n\\]\n"
        rules = [item.rule_id for item in subject.scan_text(
            text, "README.md", "github-markdown", False
        )]
        self.assertEqual(rules.count("MSM001"), 1)
        self.assertEqual(rules.count("MSM002"), 1)
        self.assertNotIn("MSM003", rules)
        self.assertNotIn("MSM004", rules)

    def test_ignores_code_and_supported_math(self):
        text = (
            "`\\(literal\\)` and $x$.\n\n"
            "```text\n\\[literal\\]\n```\n\n"
            "$$\n\\frac{a}{b}\n$$\n"
        )
        self.assertEqual(
            subject.scan_text(text, "README.md", "github-markdown", False), []
        )

    def test_native_surfaces_are_not_github_defects(self):
        text = "\\(x\\)\n\\[\ny\n\\]\n"
        self.assertEqual(subject.scan_text(text, "paper.qmd", "quarto", False), [])
        self.assertEqual(subject.scan_text(text, "paper.tex", "latex", False), [])

    def test_raw_tex_is_review(self):
        result = subject.scan_text(
            "Equation: \\dot{x}=f(x).\n", "README.md", "github-markdown", False
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].rule_id, "MSM003")
        self.assertEqual(result[0].confidence, "REVIEW")

    def test_archival_finding_is_review(self):
        result = subject.scan_text(
            "Old \\(x\\).\n", "conversation/old.md", "github-markdown", True
        )
        self.assertEqual(result[0].confidence, "REVIEW")
        self.assertFalse(result[0].fixable)

    def test_unmatched_legacy_delimiter(self):
        result = subject.scan_text(
            "\\[\nx\n", "README.md", "github-markdown", False
        )
        self.assertEqual([item.rule_id for item in result], ["MSM004"])

    def test_detects_probable_mojibake_but_accepts_valid_unicode(self):
        broken = subject.scan_text(
            "GitHubâ€™s renderer and MÃ¼ller.\n",
            "README.md", "github-markdown", False,
        )
        self.assertTrue(broken)
        self.assertTrue(all(item.rule_id == "MSM008" for item in broken))
        self.assertTrue(all(item.confidence == "REVIEW" for item in broken))
        self.assertEqual(
            subject.scan_text(
                "GitHub’s renderer and Müller.\n",
                "README.md", "github-markdown", False,
            ),
            [],
        )

    def test_reports_invalid_utf8_instead_of_silently_skipping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_bytes(b"bad utf-8: \xff\n")
            findings, scanned = subject.audit(root, subject.load_policy(root))
            self.assertEqual(scanned, 1)
            self.assertEqual([item.rule_id for item in findings], ["MSM009"])

    def test_detects_gfm_setext_collision_inside_dollar_display(self):
        result = subject.scan_text(
            "$$\nG_i^{\\mathrm{inventory}}\n=\nx\n$$\n",
            "README.md", "github-markdown", False,
        )
        self.assertEqual([item.rule_id for item in result], ["MSM010"])
        self.assertEqual(result[0].confidence, "HIGH_CONFIDENCE")
        self.assertTrue(result[0].fixable)

    def test_ignores_setext_syntax_inside_math_fence(self):
        text = "```math\nG_i^{\\mathrm{inventory}}\n=\nx\n```\n"
        self.assertEqual(
            subject.scan_text(text, "README.md", "github-markdown", False), []
        )


class RewriteTests(unittest.TestCase):
    def test_rewrites_only_visible_balanced_math(self):
        original = (
            "Inline \\(x+y\\).\n"
            "`\\(literal\\)`\n"
            "```text\n\\[literal\\]\n```\n"
            "\\[\nA=B\n\\]\n"
        )
        revised, skipped = subject.rewrite(original)
        self.assertIn("Inline $x+y$.", revised)
        self.assertIn("`\\(literal\\)`", revised)
        self.assertIn("```text\n\\[literal\\]\n```", revised)
        self.assertIn("$$\nA=B\n$$", revised)
        self.assertEqual(skipped, [])

    def test_refuses_ambiguous_dollar(self):
        original = "Cost \\(x = $5\\).\n"
        revised, skipped = subject.rewrite(original)
        self.assertEqual(revised, original)
        self.assertTrue(skipped)

    def test_semantic_hashes_cover_each_legacy_body(self):
        records = subject.legacy_semantic_hashes("Inline \\(x+y\\).\n\\[z\\]\n")
        self.assertEqual([item["display"] for item in records], [False, True])
        self.assertTrue(all(len(item["tex_sha256"]) == 64 for item in records))

    def test_rewrites_gfm_setext_collision_as_math_fence(self):
        original = "$$\nG_i^{\\mathrm{inventory}}\n=\nx\n$$\n"
        revised, skipped = subject.rewrite(original)
        self.assertEqual(
            revised,
            "```math\nG_i^{\\mathrm{inventory}}\n=\nx\n```\n",
        )
        self.assertEqual(skipped, [])
        self.assertEqual(
            subject.scan_text(revised, "README.md", "github-markdown", False), []
        )

    def test_preserves_safe_dollar_display(self):
        original = "$$\nA=B\n$$\n"
        revised, skipped = subject.rewrite(original)
        self.assertEqual(revised, original)
        self.assertEqual(skipped, [])

    def test_records_collision_body_before_and_after(self):
        original = "$$\nG_i^{\\mathrm{inventory}}\n=\nx\n$$\n"
        revised, _ = subject.rewrite(original)
        records = subject.collision_semantic_records(original, revised)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["rule_id"], "MSM010")
        self.assertTrue(records[0]["byte_identical"])
        self.assertEqual(
            records[0]["before_tex_sha256"], records[0]["after_tex_sha256"]
        )

    def test_detects_collision_body_preservation_failure(self):
        original = "$$\nG\n=\nx\n$$\n"
        altered = "```math\nG\n=\ny\n```\n"
        records = subject.collision_semantic_records(original, altered)
        self.assertFalse(records[0]["byte_identical"])
        self.assertIsNone(records[0]["after_tex_sha256"])


class StructureParityTests(unittest.TestCase):
    def test_normalizes_approved_display_container_changes(self):
        before = "Intro.\n\n\\[\nG\n=\nx\n\\]\n\nEnd.\n"
        after = "Intro.\n\n```math\nG\n=\nx\n```\n\nEnd.\n"
        self.assertEqual(
            structure.normalize_math_blocks(before),
            structure.normalize_math_blocks(after),
        )

    def test_preserves_non_math_fence_contents(self):
        text = "```text\n$$\nG\n=\nx\n$$\n```\n"
        self.assertEqual(structure.normalize_math_blocks(text), text)

    def test_skeleton_ignores_source_position_metadata(self):
        before = '<document sourcepos="1:1-1:3"><paragraph sourcepos="1:1-1:3"/></document>'
        after = '<document sourcepos="4:1-4:8"><paragraph sourcepos="4:1-4:8"/></document>'
        self.assertEqual(structure.skeleton(before), structure.skeleton(after))

    @unittest.skipUnless(
        shutil.which(os.environ.get("CMARK_GFM", "cmark-gfm")),
        "pinned cmark-gfm is not installed",
    )
    def test_cmark_accepts_math_repair_and_rejects_heading_change(self):
        executable = shutil.which(os.environ.get("CMARK_GFM", "cmark-gfm"))
        assert executable is not None
        before = "# Model\n\n$$\nG\n=\nx\n$$\n"
        repaired = "# Model\n\n```math\nG\n=\nx\n```\n"
        changed = "## Model\n\n```math\nG\n=\nx\n```\n"
        baseline = structure.structure_for_text(before, executable)
        self.assertEqual(baseline, structure.structure_for_text(repaired, executable))
        self.assertNotEqual(baseline, structure.structure_for_text(changed, executable))


class ReportAndExtractionTests(unittest.TestCase):
    def test_git_inventory_includes_nonignored_untracked_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text("ignored.md\n", encoding="utf-8")
            (root / "tracked.md").write_text("Tracked.\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", ".gitignore", "tracked.md"],
                check=True,
            )
            (root / "new.md").write_text("New.\n", encoding="utf-8")
            (root / "ignored.md").write_text("Ignored.\n", encoding="utf-8")
            files = subject.files_for(root, subject.load_policy(root))
            self.assertEqual(
                [item.relative_to(root).as_posix() for item in files],
                ["new.md", "tracked.md"],
            )

    def test_inline_extraction_does_not_cross_adjacent_expressions(self):
        self.assertEqual(
            subject.inline_dollar_fragments(
                "where $S$ is a system, $H$ a hazard, and $C=\\$5$ a cost"
            ),
            ["S", "H", "C=\\$5"],
        )

    def test_sarif_shape(self):
        result = subject.scan_text(
            "Inline \\(x\\).\n", "README.md", "github-markdown", False
        )
        data = json.loads(subject.render_sarif(result))
        self.assertEqual(data["version"], "2.1.0")
        self.assertEqual(data["runs"][0]["results"][0]["ruleId"], "MSM001")

    def test_repository_audit_and_extract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text(
                "Bad \\(x\\).\nGood $y$.\n\n$$\nz\n$$\n", encoding="utf-8"
            )
            policy = subject.load_policy(root)
            findings, scanned = subject.audit(root, policy)
            self.assertEqual(scanned, 1)
            self.assertEqual([item.rule_id for item in findings], ["MSM001"])
            fragments = subject.extract(root, policy)
            self.assertEqual(len(fragments), 2)
            self.assertEqual({item["display"] for item in fragments}, {False, True})


if __name__ == "__main__":
    unittest.main()
