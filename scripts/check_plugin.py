from __future__ import annotations

import re
import sys
from pathlib import Path


CHILDREN: dict[str, str] = {
    "check-security": "SEC",
    "check-general": "GC",
    "check-db-migration": "DB",
    "check-rails-app": "RB",
    "check-frontend": "FE",
    "check-deps-ci-config": "DC",
    "check-tests": "TE",
    "check-docs": "DOC",
}

REQUIRED_MUST_CHECK: dict[str, list[str]] = {
    "check-security": ["SEC1", "SEC2", "SEC6", "SEC14", "SEC33"],
    "check-general": ["GC1", "GC2", "GC3", "GC6"],
    "check-rails-app": ["RB1", "RB2", "RB4"],
    "check-db-migration": ["DB1", "DB2", "DB3", "DB4", "DB6"],
    "check-frontend": ["FE24", "FE34", "FE35"],
    "check-tests": ["TE1", "TE2"],
    "check-deps-ci-config": ["DC2", "DC3", "DC12", "DC15", "DC21"],
    "check-docs": ["DOC1", "DOC2"],
}

_TABLE_ID = re.compile(r"^\|\s*([A-Z]+\d+)\s*\|")
_MUST_CHECK_ID = re.compile(r"^- \*\*([A-Z]+\d+)\*\*")


def parse_frontmatter(text: str) -> dict[str, str]:
    """Return simple top-level key/value pairs from leading YAML frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}

    frontmatter: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            return frontmatter
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()
    return {}


def table_ids(text: str) -> list[str]:
    """Return IDs from Markdown table rows in source order."""
    return [match.group(1) for line in text.splitlines() if (match := _TABLE_ID.match(line))]


def must_check_ids(skill_text: str) -> list[str]:
    """Return IDs in the 必ず探す項目 section, stopping at the next H2."""
    lines = skill_text.splitlines()
    try:
        start = lines.index("## 必ず探す項目") + 1
    except ValueError:
        return []

    ids: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if match := _MUST_CHECK_ID.match(line):
            ids.append(match.group(1))
    return ids


def _body_line_count(text: str) -> int:
    lines = text.splitlines()
    if lines and lines[0] == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line == "---":
                return len(lines[index + 1 :])
    return len(lines)


def _read_text(path: Path, errors: list[str], label: str) -> str | None:
    if not path.is_file():
        errors.append(f"{label}: SKILL.md がない")
        return None
    return path.read_text(encoding="utf-8")


def _check_skill_metadata(skill_name: str, text: str, errors: list[str]) -> None:
    frontmatter = parse_frontmatter(text)
    if "name" not in frontmatter:
        errors.append(f"{skill_name}: name がない")
    elif frontmatter["name"] != skill_name:
        errors.append(f"{skill_name}: name がディレクトリ名と一致しない")

    description = frontmatter.get("description")
    if not description:
        errors.append(f"{skill_name}: description がない")
    elif len(description) > 1024:
        errors.append(f"{skill_name}: description が 1,024 文字を超えている")

    if _body_line_count(text) >= 500:
        errors.append(f"{skill_name}: 本文が 500 行以上ある")


FORBIDDEN_ALLOWED_TOOLS = (
    "Bash(git update-ref *)",
    "Bash(git worktree *)",
    "Bash(gh api *)",
    "Bash(git *)",
    "Bash(gh *)",
    "Bash(*)",
    "Bash",
    "Edit",
    "Write",
)


def _check_allowed_tools(skill_name: str, text: str, errors: list[str]) -> None:
    allowed = parse_frontmatter(text).get("allowed-tools", "")
    entries = re.findall(r"\w+\([^)]*\)|\w+", allowed)
    for entry in entries:
        if entry in FORBIDDEN_ALLOWED_TOOLS:
            errors.append(f"{skill_name}: allowed-tools に広すぎる事前許可がある: {entry}")


def check_plugin(root: Path, report_path: Path) -> list[str]:
    """Validate the plugin's skill structure and generated child checklists."""
    errors: list[str] = []
    skills_root = root / "plugins" / "rails-ts-pr-review" / "skills"

    review_text = _read_text(skills_root / "review" / "SKILL.md", errors, "review")
    if review_text is not None:
        _check_skill_metadata("review", review_text, errors)
        _check_allowed_tools("review", review_text, errors)

    report_ids = table_ids(report_path.read_text(encoding="utf-8"))
    for skill_name, prefix in CHILDREN.items():
        skill_root = skills_root / skill_name
        skill_text = _read_text(skill_root / "SKILL.md", errors, skill_name)
        if skill_text is None:
            continue

        _check_skill_metadata(skill_name, skill_text, errors)
        frontmatter = parse_frontmatter(skill_text)
        if frontmatter.get("user-invocable") != "false":
            errors.append(f"{skill_name}: user-invocable: false が必要")

        checklist_path = skill_root / "references" / "checklist.md"
        if not checklist_path.is_file():
            errors.append(f"{skill_name}: references/checklist.md がない")
            checklist_ids: list[str] = []
        else:
            checklist_ids = table_ids(checklist_path.read_text(encoding="utf-8"))

        expected_ids = [item_id for item_id in report_ids if item_id.startswith(prefix)]
        duplicate_ids = sorted({item_id for item_id in checklist_ids if checklist_ids.count(item_id) > 1})
        for item_id in duplicate_ids:
            errors.append(f"{skill_name}: checklist の ID が重複している: {item_id}")

        if set(checklist_ids) != set(expected_ids):
            for item_id in expected_ids:
                if item_id not in checklist_ids:
                    errors.append(f"{skill_name}: checklist に {item_id} がない")
            for item_id in checklist_ids:
                if item_id not in expected_ids:
                    errors.append(f"{skill_name}: checklist に不要な ID がある: {item_id}")

        must_ids = must_check_ids(skill_text)
        if not 3 <= len(must_ids) <= 8:
            errors.append(f"{skill_name}: 必ず探す項目は 3〜8 個必要")
        for item_id in must_ids:
            if item_id not in checklist_ids:
                errors.append(f"{skill_name}: 必ず探す項目の {item_id} が checklist にない")
        for item_id in REQUIRED_MUST_CHECK[skill_name]:
            if item_id not in must_ids:
                errors.append(f"{skill_name}: 必ず探す項目に {item_id} がない")

    return errors


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    errors = check_plugin(Path("."), Path("docs/research/report.md"))
    if errors:
        print("\n".join(errors))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
