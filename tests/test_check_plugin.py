from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_plugin import (  # type: ignore[import-not-found]
    REQUIRED_MUST_CHECK,
    check_plugin,
    must_check_ids,
    parse_frontmatter,
    table_ids,
)


REQUIRED = {
    "check-security": ["SEC1", "SEC2", "SEC6", "SEC14", "SEC33"],
    "check-general": ["GC1", "GC2", "GC3", "GC6"],
    "check-rails-app": ["RB1", "RB2", "RB4"],
    "check-db-migration": ["DB1", "DB2", "DB3", "DB4", "DB6"],
    "check-frontend": ["FE24", "FE34", "FE35"],
    "check-tests": ["TE1", "TE2"],
    "check-deps-ci-config": ["DC2", "DC3", "DC12", "DC15", "DC21"],
    "check-docs": ["DOC1", "DOC2"],
}


class TestParsers(unittest.TestCase):
    def test_parse_frontmatter(self):
        frontmatter = parse_frontmatter(
            "---\nname: review\ndescription: x y\nuser-invocable: false\n---\nbody"
        )
        self.assertEqual(
            frontmatter,
            {"name": "review", "description": "x y", "user-invocable": "false"},
        )

    def test_parse_frontmatter_missing(self):
        self.assertEqual(parse_frontmatter("no frontmatter"), {})

    def test_table_ids(self):
        text = "| # | 観点 |\n|---|---|\n| SEC1 | a |\n| SEC2 | b |\ntext | SEC9 | no\n"
        self.assertEqual(table_ids(text), ["SEC1", "SEC2"])

    def test_must_check_ids(self):
        text = "## 必ず探す項目\n- **RB1**: n+1\n- **RB2**: x\n\n## 手順\n- **RB3**: not here\n"
        self.assertEqual(must_check_ids(text), ["RB1", "RB2"])

    def test_required_constant(self):
        self.assertEqual(REQUIRED_MUST_CHECK, REQUIRED)


class TestCheckPlugin(unittest.TestCase):
    def make_valid_plugin(self, directory: Path) -> tuple[Path, Path]:
        root = directory / "root"
        skills = root / "plugins" / "rails-ts-pr-review" / "skills"
        report_rows: list[str] = []

        (skills / "review").mkdir(parents=True)
        (skills / "review" / "SKILL.md").write_text(
            "---\nname: review\ndescription: Parent review skill\n---\nbody\n",
            encoding="utf-8",
            newline="\n",
        )

        for skill_name, required_ids in REQUIRED.items():
            prefix = "".join(character for character in required_ids[0] if character.isalpha())
            ids = required_ids + [f"{prefix}99"]
            report_rows.extend(f"| {item_id} | item | must | diff | source |" for item_id in ids)

            skill_directory = skills / skill_name
            references = skill_directory / "references"
            references.mkdir(parents=True)
            skill_directory.joinpath("SKILL.md").write_text(
                "---\n"
                f"name: {skill_name}\n"
                "description: Child review skill\n"
                "user-invocable: false\n"
                "---\n"
                "## 必ず探す項目\n"
                + "".join(f"- **{item_id}**: required\n" for item_id in ids)
                + "\n## 手順\nbody\n",
                encoding="utf-8",
                newline="\n",
            )
            references.joinpath("checklist.md").write_text(
                "\n".join(f"| {item_id} | item |" for item_id in ids) + "\n",
                encoding="utf-8",
                newline="\n",
            )

        report_path = root / "docs" / "research" / "report.md"
        report_path.parent.mkdir(parents=True)
        report_path.write_text("\n".join(report_rows) + "\n", encoding="utf-8", newline="\n")
        return root, report_path

    def assert_error_contains(self, errors: list[str], expected: str):
        self.assertTrue(any(expected in error for error in errors), errors)

    def test_valid_plugin_has_no_errors(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, report_path = self.make_valid_plugin(Path(temporary_directory))
            self.assertEqual(check_plugin(root, report_path), [])

    def test_missing_child_skill(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, report_path = self.make_valid_plugin(Path(temporary_directory))
            (root / "plugins/rails-ts-pr-review/skills/check-docs/SKILL.md").unlink()
            self.assert_error_contains(check_plugin(root, report_path), "check-docs: SKILL.md がない")

    def test_child_must_not_be_user_invocable(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, report_path = self.make_valid_plugin(Path(temporary_directory))
            skill = root / "plugins/rails-ts-pr-review/skills/check-general/SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8").replace("user-invocable: false\n", ""), encoding="utf-8", newline="\n")
            self.assert_error_contains(check_plugin(root, report_path), "user-invocable: false")

    def test_missing_description(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, report_path = self.make_valid_plugin(Path(temporary_directory))
            skill = root / "plugins/rails-ts-pr-review/skills/check-general/SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8").replace("description: Child review skill\n", ""), encoding="utf-8", newline="\n")
            self.assert_error_contains(check_plugin(root, report_path), "description")

    def test_body_too_long(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, report_path = self.make_valid_plugin(Path(temporary_directory))
            skill = root / "plugins/rails-ts-pr-review/skills/check-general/SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "line\n" * 500, encoding="utf-8", newline="\n")
            self.assert_error_contains(check_plugin(root, report_path), "500")

    def test_checklist_id_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, report_path = self.make_valid_plugin(Path(temporary_directory))
            checklist = root / "plugins/rails-ts-pr-review/skills/check-general/references/checklist.md"
            checklist.write_text(checklist.read_text(encoding="utf-8").replace("| GC99 | item |\n", ""), encoding="utf-8", newline="\n")
            self.assert_error_contains(check_plugin(root, report_path), "GC99")

    def test_checklist_id_duplicated(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, report_path = self.make_valid_plugin(Path(temporary_directory))
            checklist = root / "plugins/rails-ts-pr-review/skills/check-general/references/checklist.md"
            checklist.write_text(checklist.read_text(encoding="utf-8") + "| GC1 | item |\n", encoding="utf-8", newline="\n")
            self.assert_error_contains(check_plugin(root, report_path), "重複")

    def test_must_check_count_bounds(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, report_path = self.make_valid_plugin(Path(temporary_directory))
            skill = root / "plugins/rails-ts-pr-review/skills/check-general/SKILL.md"
            text = skill.read_text(encoding="utf-8")
            skill.write_text(
                text.replace("- **GC2**: required\n", "").replace("- **GC3**: required\n", "").replace("- **GC6**: required\n", ""),
                encoding="utf-8",
                newline="\n",
            )
            self.assert_error_contains(check_plugin(root, report_path), "3〜8")

            root, report_path = self.make_valid_plugin(Path(temporary_directory) / "many")
            skill = root / "plugins/rails-ts-pr-review/skills/check-general/SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8").replace("\n## 手順", "\n" + "".join(f"- **GC{number}**: item\n" for number in range(40, 47)) + "\n## 手順"), encoding="utf-8", newline="\n")
            self.assert_error_contains(check_plugin(root, report_path), "3〜8")

    def test_must_check_not_in_checklist(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, report_path = self.make_valid_plugin(Path(temporary_directory))
            skill = root / "plugins/rails-ts-pr-review/skills/check-general/SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8").replace("- **GC3**: required", "- **GC404**: required"), encoding="utf-8", newline="\n")
            self.assert_error_contains(check_plugin(root, report_path), "GC404")

    def test_required_must_check_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, report_path = self.make_valid_plugin(Path(temporary_directory))
            skill = root / "plugins/rails-ts-pr-review/skills/check-rails-app/SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8").replace("- **RB4**: required\n", ""), encoding="utf-8", newline="\n")
            self.assert_error_contains(check_plugin(root, report_path), "RB4")
