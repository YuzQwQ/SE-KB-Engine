#!/usr/bin/env python
"""仓库文本文件编码普查（BOOT-001）。

检查所有受版本控制的 .py/.md/.json/.txt/.toml/.cfg/.yml/.yaml 文件：
- 是否可按 UTF-8 无损解码
- Python 文件是否能通过编译（BOOT-005）

用法:
    python scripts/check_encodings.py            # 普查 + 编译检查
    python scripts/check_encodings.py --no-compile   # 仅编码普查
退出码: 0 = 全部正常, 1 = 存在异常文件
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".txt",
    ".toml",
    ".cfg",
    ".yml",
    ".yaml",
    ".example",
    ".gitignore",
}

# 运行产物/外部目录不参与检查（BASE-006 类目见 backlog）
EXCLUDED_DIRS = {
    ".venv",
    "venv",
    "venv_enhanced",
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".tmp",
    "__pycache__",
    "node_modules",
    "output",
    "data",
    "shared_data",
    "se_kb/artifacts",
    "se_kb/vector_store",
    ".tor_data",
    "tor_data",
    "test_output",
    "Test",
}

EXCLUDED_FILES = {
    "old_format_files.txt",
    "processed_files_record.json",
    "quality_report.json",
    "reorganization_log.json",
}


def iter_target_files(root: Path = PROJECT_ROOT) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        parts = set(Path(rel).parts)
        if path.name in EXCLUDED_FILES:
            continue
        if any("/" not in ex and ex in parts for ex in EXCLUDED_DIRS):
            continue
        if any("/" in ex and (rel == ex or rel.startswith(f"{ex}/")) for ex in EXCLUDED_DIRS):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name == ".gitignore":
            files.append(path)
    return sorted(files)


def check_utf8(path: Path) -> str | None:
    """返回异常描述；None 表示正常。"""
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return "UTF-16 BOM 检测到（应转为 UTF-8）"
    if raw.startswith(b"\xef\xbb\xbf"):
        return "UTF-8 BOM（建议去除，保持无 BOM UTF-8）"
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return f"UTF-8 解码失败: {exc}"
    return None


def check_compile(path: Path) -> str | None:
    if path.suffix != ".py":
        return None
    try:
        source = path.read_text(encoding="utf-8")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            compile(source, str(path), "exec")
    except (SyntaxError, ValueError) as exc:
        return f"编译失败: {exc}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-compile", action="store_true", help="跳过 Python 编译检查")
    parser.add_argument("--root", help="扫描指定根目录（测试和诊断使用）")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else PROJECT_ROOT
    files = iter_target_files(root)
    bad: list[tuple[Path, str]] = []

    for path in files:
        issue = check_utf8(path)
        if issue:
            bad.append((path, issue))
        if not args.no_compile and issue is None:
            issue = check_compile(path)
            if issue:
                bad.append((path, issue))

    print(f"扫描 {len(files)} 个文本文件（含 {sum(1 for f in files if f.suffix == '.py')} 个 Python 文件）")
    if not bad:
        print("编码与编译检查: 全部通过")
        return 0
    print(f"发现 {len(bad)} 个异常:")
    for path, issue in bad:
        print(f"  {path.relative_to(root)}: {issue}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
