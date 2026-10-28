from __future__ import annotations

import re
from pathlib import Path

from check_plugin import CHILDREN


_TABLE_ROW = re.compile(r"^\|\s*([A-Z]+)(\d+)\s*\|")
_LEGEND = (
    "凡例は次のとおり。**既定**は重要度の初期値で、must はマージ前に必須、should は強く推奨（理由があれば見送り可）、"
    "nit は任意を表す。検証段階で上げ下げできる。**判定**は、指摘に必要な情報の範囲を表す。diff は差分だけで判断できる、"
    "repo は呼び出し元・スキーマ・設定・lint 設定などリポジトリ文脈が必要、PR は PR 説明やチケットが必要、"
    "実行は実機・CI 結果・本番統計・外部レジストリが必要、という意味だ。判定が「実行」の項目は静的レビューでは確定できないので、"
    "カバレッジ報告で「人間による確認が必要」と明示する。出典が「慣行」の項目は、権威ある単一の一次情報が見つからなかったものだ。"
)
_OUTPUT_PREFIX_ORDER = ("GC", "SEC", "RB", "DB", "FE", "TE", "DC", "DOC")


def extract_rows(report_text: str) -> dict[str, list[str]]:
    """Group original checklist rows by the child-skill ID prefixes."""
    prefixes = set(CHILDREN.values())
    rows: dict[str, list[str]] = {}
    for line in report_text.splitlines():
        match = _TABLE_ROW.match(line)
        if match is None or match.group(1) not in prefixes:
            continue
        rows.setdefault(match.group(1), []).append(line)
    return rows


def render_checklist(skill_name: str, prefix: str, rows: list[str]) -> str:
    """Render a generated child-skill checklist using its original report rows."""
    return "\n".join(
        [
            f"# {skill_name} チェックリスト",
            "",
            "このファイルは scripts/extract_checklists.py で docs/research/report.md から生成。直接編集しない。",
            "",
            _LEGEND,
            "",
            "| # | 観点 | 既定 | 判定 | 出典 |",
            "|---|---|---|---|---|",
            *rows,
            "",
        ]
    )


def main() -> int:
    root = Path(".")
    rows_by_prefix = extract_rows((root / "docs" / "research" / "report.md").read_text(encoding="utf-8"))
    skills_root = root / "plugins" / "rails-ts-pr-review" / "skills"

    for skill_name, prefix in CHILDREN.items():
        output_path = skills_root / skill_name / "references" / "checklist.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
            output_file.write(render_checklist(skill_name, prefix, rows_by_prefix.get(prefix, [])))

    print(" ".join(f"{prefix}{len(rows_by_prefix.get(prefix, []))}" for prefix in _OUTPUT_PREFIX_ORDER))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
