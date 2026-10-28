from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from extract_checklists import extract_rows, render_checklist  # type: ignore[import-not-found]


HEADER = "| # | \u89b3\u70b9 | \u65e2\u5b9a | \u5224\u5b9a | \u51fa\u5178 |"
REPORT = "\n".join(
    [
        HEADER,
        "|---|---|---|---|---|",
        "| GC1 | a | must | diff | x |",
        "| SEC1 | b | must | repo | y |",
        "| SEC2 | c | should | diff | z |",
        "| P1 | parent | should | PR | w |",
    ]
)


class TestExtractChecklists(unittest.TestCase):
    def test_extract_rows_groups_by_prefix(self):
        rows = extract_rows(REPORT)
        self.assertEqual(rows["SEC"], ["| SEC1 | b | must | repo | y |", "| SEC2 | c | should | diff | z |"])
        self.assertEqual(rows["GC"], ["| GC1 | a | must | diff | x |"])
        self.assertNotIn("P", rows)

    def test_render_checklist(self):
        output = render_checklist("check-security", "SEC", ["| SEC1 | b | must | repo | y |"])
        self.assertTrue(output.startswith("# check-security \u30c1\u30a7\u30c3\u30af\u30ea\u30b9\u30c8\n"))
        self.assertIn(HEADER, output)
        self.assertIn("| SEC1 | b | must | repo | y |", output)
        self.assertIn("\u76f4\u63a5\u7de8\u96c6\u3057\u306a\u3044", output)

    def test_real_report_counts(self):
        rows = extract_rows(Path("docs/research/report.md").read_text(encoding="utf-8"))
        self.assertEqual(
            {prefix: len(items) for prefix, items in rows.items()},
            {"GC": 15, "SEC": 33, "RB": 28, "DB": 26, "FE": 36, "TE": 14, "DC": 22, "DOC": 9},
        )

