#!/usr/bin/env python3
"""维护 review-package-v1；仅使用 Python 标准库。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path, PurePosixPath
from typing import Any

VERSION = "review-package-v1"
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
HASH_RE = re.compile(r"^[a-f0-9]{64}$")
REQUIREMENT_ID_RE = re.compile(r"REQ-\d{3}(?:\.\d+)*")
REQUIREMENT_HEADING_RE = re.compile(
    r"^(#{2,6})\s+(REQ-\d{3}(?:\.\d+)*)\s+(.+?)\s*$", re.MULTILINE
)
EMPTY_WORDS = re.compile(
    r"(请填写|待补充|TODO|TBD|待确认|后续完善|同上|满足需求|优化逻辑)",
    re.IGNORECASE,
)
LANGUAGES = {
    ".c": "c", ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp", ".h": "cpp",
    ".hh": "cpp", ".hpp": "cpp", ".inl": "cpp", ".cs": "csharp",
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".json": "json",
    ".md": "markdown", ".xml": "xml", ".yaml": "yaml", ".yml": "yaml",
    ".ini": "ini", ".lua": "lua", ".usf": "cpp", ".ush": "cpp",
}
MANIFEST_KEYS = {
    "schemaVersion", "changeId", "title", "sourceRoot",
    "createdAt", "updatedAt", "files",
}
TRACKED_FILE_KEYS = {
    "id", "fileName", "sourcePath", "originalPath",
    "originalHash", "status", "language",
}
REVIEW_KEYS = {"schemaVersion", "changeId", "readingOrder", "files"}
FILE_REVIEW_KEYS = {"fileId", "changes"}
CHANGE_KEYS = {
    "id", "title", "kind", "before", "after",
    "originalLogic", "modifiedLogic", "requirementRelation",
}
RANGE_KEYS = {"startLine", "endLine", "contentHash"}


class ReviewError(RuntimeError):
    pass


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReviewError(f"缺少文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ReviewError(f"JSON 格式错误：{path}（{exc}）") from exc
    if not isinstance(value, dict):
        raise ReviewError(f"JSON 顶层必须是对象：{path}")
    return value


def save(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def source_root(value: str | None) -> Path:
    root = Path(value).resolve() if value else Path.cwd().resolve()
    if not root.is_dir():
        raise ReviewError(f"源工程目录不存在：{root}")
    return root


def check_id(change_id: str) -> None:
    if not ID_RE.fullmatch(change_id) or not 3 <= len(change_id) <= 80:
        raise ReviewError("修改标识必须是 3-80 位英文 kebab-case")


def package(root: Path, change_id: str) -> Path:
    check_id(change_id)
    return root / "MyCocs" / change_id


def source_file(root: Path, value: str) -> tuple[Path, str]:
    candidate = Path(value)
    absolute = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        relative = absolute.relative_to(root)
    except ValueError as exc:
        raise ReviewError(f"文件必须位于源工程内：{absolute}") from exc
    if (
        not relative.parts
        or relative.parts[0].lower() == "mycocs"
        or relative.parts[0].startswith(".")
    ):
        raise ReviewError(f"不能登记该路径：{relative}")
    return absolute, PurePosixPath(*relative.parts).as_posix()


def original_file(folder: Path, tracked: dict[str, Any]) -> Path | None:
    value = tracked.get("originalPath")
    if value is None:
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        raise ReviewError(f"非法备份路径：{value}")
    result = folder.joinpath(*pure.parts).resolve()
    try:
        result.relative_to(folder.resolve())
    except ValueError as exc:
        raise ReviewError(f"备份路径越界：{value}") from exc
    return result


def lines(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError as exc:
        raise ReviewError(f"只支持 UTF-8 文本文件：{path}") from exc


def code_range(content: list[str], start: int, end: int) -> dict[str, Any]:
    if start == end:
        return {"startLine": 0, "endLine": 0, "contentHash": ""}
    return {
        "startLine": start + 1,
        "endLine": end,
        "contentHash": hash_text("\n".join(content[start:end])),
    }


def diff_ranges(before: list[str], after: list[str]) -> list[tuple[int, int, int, int]]:
    changed = [
        opcode for opcode in SequenceMatcher(
            None, before, after, autojunk=False
        ).get_opcodes() if opcode[0] != "equal"
    ]
    if not changed:
        return []
    groups = [[changed[0]]]
    for opcode in changed[1:]:
        previous = groups[-1][-1]
        if opcode[1] - previous[2] <= 2 and opcode[3] - previous[4] <= 2:
            groups[-1].append(opcode)
        else:
            groups.append([opcode])
    return [
        (group[0][1], group[-1][2], group[0][3], group[-1][4])
        for group in groups
    ]


def changes(
    before: list[str], after: list[str], old: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    previous = {
        item.get("id"): item for item in (old or []) if isinstance(item, dict)
    }
    result = []
    for b1, b2, a1, a2 in diff_ranges(before, after):
        before_range, after_range = code_range(before, b1, b2), code_range(after, a1, a2)
        kind = "add" if b1 == b2 else ("delete" if a1 == a2 else "modify")
        identity = f"{kind}|{before_range['contentHash']}|{after_range['contentHash']}"
        block_id = "change-" + hashlib.sha1(identity.encode()).hexdigest()[:12]
        saved = previous.get(block_id, {})
        result.append({
            "id": block_id,
            "title": saved.get("title", ""),
            "kind": kind,
            "before": before_range,
            "after": after_range,
            "originalLogic": saved.get("originalLogic", ""),
            "modifiedLogic": saved.get("modifiedLogic", ""),
            "requirementRelation": saved.get("requirementRelation", ""),
        })
    return result


def init(args: argparse.Namespace) -> None:
    root = source_root(args.source_root)
    folder = package(root, args.change_id)
    if folder.exists():
        raise ReviewError(f"审核包已存在，请复用：{folder}")
    (folder / "originals").mkdir(parents=True)
    (folder / "docs").mkdir()
    now = timestamp()
    save(folder / "files.json", {
        "schemaVersion": VERSION, "changeId": args.change_id, "title": args.title,
        "sourceRoot": ".", "createdAt": now, "updatedAt": now, "files": [],
    })
    save(folder / "review.json", {
        "schemaVersion": VERSION, "changeId": args.change_id,
        "readingOrder": [], "files": [],
    })
    print(f"已创建审核包：{folder}")


def backup(args: argparse.Namespace) -> None:
    root, change_id = source_root(args.source_root), args.change_id
    folder = package(root, change_id)
    manifest, review = load(folder / "files.json"), load(folder / "review.json")
    current, relative = source_file(root, args.file)
    if any(item.get("sourcePath") == relative for item in manifest.get("files", [])):
        print(f"原始快照已存在，未覆盖：{relative}")
        return
    file_id = "file-" + hashlib.sha1(relative.lower().encode()).hexdigest()[:12]
    if current.exists():
        original_path = PurePosixPath("originals", *Path(relative).parts).as_posix()
        original = folder.joinpath(*PurePosixPath(original_path).parts)
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(current, original)
        original_hash, status = hash_bytes(original.read_bytes()), "modified"
    elif args.added:
        original_path, original_hash, status = None, None, "added"
    else:
        raise ReviewError(f"文件不存在；准备新增时请加 --added：{current}")
    manifest.setdefault("files", []).append({
        "id": file_id, "fileName": Path(relative).name, "sourcePath": relative,
        "originalPath": original_path, "originalHash": original_hash,
        "status": status, "language": LANGUAGES.get(Path(relative).suffix.lower(), "plaintext"),
    })
    manifest["updatedAt"] = timestamp()
    review.setdefault("readingOrder", []).append(file_id)
    review.setdefault("files", []).append({"fileId": file_id, "changes": []})
    save(folder / "files.json", manifest)
    save(folder / "review.json", review)
    print(f"已登记原始状态：{relative}（{status}）")


def sync(args: argparse.Namespace) -> None:
    root, change_id = source_root(args.source_root), args.change_id
    folder = package(root, change_id)
    manifest, review = load(folder / "files.json"), load(folder / "review.json")
    old = {
        item.get("fileId"): item for item in review.get("files", [])
        if isinstance(item, dict)
    }
    reviews = []
    for tracked in manifest.get("files", []):
        current, _ = source_file(root, tracked["sourcePath"])
        original = original_file(folder, tracked)
        if original is None and not current.exists():
            raise ReviewError(f"新增文件尚不存在：{current}")
        if original is not None and not original.exists():
            raise ReviewError(f"原始备份丢失：{original}")
        tracked["status"] = "added" if original is None else (
            "modified" if current.exists() else "deleted"
        )
        modified = folder.joinpath(
            "modified", *PurePosixPath(tracked["sourcePath"]).parts
        )
        if current.exists():
            modified.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(current, modified)
        elif modified.exists():
            modified.unlink()
        saved = old.get(tracked["id"], {})
        reviews.append({
            "fileId": tracked["id"],
            "changes": changes(
                lines(original), lines(current if current.exists() else None),
                saved.get("changes", []),
            ),
        })
    ids = [item["id"] for item in manifest.get("files", [])]
    kept = [item for item in review.get("readingOrder", []) if item in ids]
    review["readingOrder"] = kept + [item for item in ids if item not in kept]
    review["files"] = reviews
    manifest["updatedAt"] = timestamp()
    save(folder / "files.json", manifest)
    save(folder / "review.json", review)
    print(f"已同步 {len(ids)} 个文件、{sum(len(x['changes']) for x in reviews)} 个改动块。")


def explain(value: Any, label: str, minimum: int, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append(f"{label} 必须是字符串")
        return
    compact = re.sub(r"\s+", "", value)
    if len(compact) < minimum:
        errors.append(f"{label} 过于简略，至少 {minimum} 个非空白字符")
    if EMPTY_WORDS.search(value):
        errors.append(f"{label} 含占位或空泛表述")
    if len(re.findall(r"[\u4e00-\u9fff]", value)) < max(6, minimum // 3):
        errors.append(f"{label} 应使用清楚的中文说明")


def exact_keys(
    value: dict[str, Any], expected: set[str], label: str, errors: list[str]
) -> None:
    actual = set(value)
    missing = expected - actual
    extra = actual - expected
    if missing:
        errors.append(f"{label} 缺少字段：{', '.join(sorted(missing))}")
    if extra:
        errors.append(f"{label} 包含未声明字段：{', '.join(sorted(extra))}")


def check_requirements(folder: Path, errors: list[str]) -> tuple[set[str], set[str]]:
    requirement_path = folder / "docs" / "用户需求.md"
    try:
        content = requirement_path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        errors.append("缺少用户需求文档：docs/用户需求.md")
        return set(), set()
    except UnicodeDecodeError:
        errors.append("docs/用户需求.md 必须是 UTF-8 文本")
        return set(), set()
    if not content.lstrip().startswith("# 用户需求"):
        errors.append("docs/用户需求.md 必须以“# 用户需求”开头")
    matches = list(REQUIREMENT_HEADING_RE.finditer(content))
    if not matches:
        errors.append("用户需求文档至少要包含一个 REQ-001 层级需求")
    requirement_ids: set[str] = set()
    for index, match in enumerate(matches):
        marks, requirement_id, title = match.groups()
        prefix = f"用户需求 {requirement_id}"
        if requirement_id in requirement_ids:
            errors.append(f"{prefix} 编号重复")
        requirement_ids.add(requirement_id)
        depth = requirement_id.count(".") + 1
        if len(marks) != depth + 1:
            errors.append(
                f"{prefix} 的标题层级错误：编号深度 {depth} 必须使用 {'#' * (depth + 1)}"
            )
        if "." in requirement_id:
            parent = requirement_id.rsplit(".", 1)[0]
            if parent not in requirement_ids:
                errors.append(f"{prefix} 缺少父需求 {parent}，或父需求没有写在它前面")
        if len(re.sub(r"\s+", "", title)) < 4:
            errors.append(f"{prefix} 的标题过于简略")
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        body = content[match.end():section_end]
        if len(re.sub(r"\s+", "", body)) < 24:
            errors.append(f"{prefix} 的说明过于简略，至少需要 24 个非空白字符")
        if EMPTY_WORDS.search(body):
            errors.append(f"{prefix} 含占位或空泛表述")
    leaves = {
        requirement_id for requirement_id in requirement_ids
        if not any(other.startswith(requirement_id + ".") for other in requirement_ids)
    }
    return requirement_ids, leaves


def validate(args: argparse.Namespace) -> None:
    root, change_id = source_root(args.source_root), args.change_id
    folder = package(root, change_id)
    manifest, review = load(folder / "files.json"), load(folder / "review.json")
    errors: list[str] = []
    requirement_ids, leaf_ids = check_requirements(folder, errors)
    exact_keys(manifest, MANIFEST_KEYS, "files.json", errors)
    exact_keys(review, REVIEW_KEYS, "review.json", errors)
    for name, document in (("files.json", manifest), ("review.json", review)):
        if document.get("schemaVersion") != VERSION:
            errors.append(f"{name}.schemaVersion 必须是 {VERSION}")
        if document.get("changeId") != change_id:
            errors.append(f"{name}.changeId 与目录名不一致")
    if manifest.get("sourceRoot") != ".":
        errors.append("files.json.sourceRoot 必须固定为 .")
    if not isinstance(manifest.get("title"), str) or len(manifest.get("title", "")) < 2:
        errors.append("files.json.title 不能为空")
    for field in ("createdAt", "updatedAt"):
        value = manifest.get(field)
        try:
            if not isinstance(value, str):
                raise ValueError
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError
        except ValueError:
            errors.append(f"files.json.{field} 必须是带时区的 ISO 8601 时间")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        errors.append("审核包至少要登记一个文件")
        files = []
    ids, paths, tracked_by_id = [], set(), {}
    for index, tracked in enumerate(files):
        prefix = f"files[{index}]"
        if not isinstance(tracked, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        exact_keys(tracked, TRACKED_FILE_KEYS, prefix, errors)
        file_id, relative = tracked.get("id"), tracked.get("sourcePath")
        if not isinstance(file_id, str) or not re.fullmatch(r"file-[a-f0-9]{12}", file_id):
            errors.append(f"{prefix}.id 格式错误")
            continue
        if not isinstance(relative, str) or not relative:
            errors.append(f"{prefix}.sourcePath 不能为空")
            continue
        if file_id in ids or relative in paths:
            errors.append(f"{prefix} 存在重复 ID 或路径")
        ids.append(file_id)
        paths.add(relative)
        tracked_by_id[file_id] = tracked
        if tracked.get("fileName") != Path(relative).name:
            errors.append(f"{prefix}.fileName 必须与 sourcePath 文件名一致")
        if tracked.get("status") not in {"added", "modified", "deleted"}:
            errors.append(f"{prefix}.status 只能是 added、modified、deleted")
        if not isinstance(tracked.get("language"), str) or not tracked.get("language"):
            errors.append(f"{prefix}.language 不能为空")
        try:
            current, normalized = source_file(root, relative)
            if normalized != relative.replace("\\", "/"):
                errors.append(f"{prefix}.sourcePath 必须使用规范正斜杠")
            original = original_file(folder, tracked)
            if original is None:
                if tracked.get("status") != "added":
                    errors.append(f"{prefix}.status 没有原始快照时必须为 added")
                if tracked.get("originalPath") is not None:
                    errors.append(f"{prefix}.originalPath 新增文件必须为 null")
                if tracked.get("originalHash") is not None:
                    errors.append(f"{prefix}.originalHash 新增文件必须为 null")
                if not current.exists():
                    errors.append(f"新增文件不存在：{relative}")
            else:
                expected_original = PurePosixPath(
                    "originals", *Path(relative).parts
                ).as_posix()
                if tracked.get("originalPath") != expected_original:
                    errors.append(
                        f"{prefix}.originalPath 必须是 {expected_original}"
                    )
                if tracked.get("status") == "added":
                    errors.append(f"{prefix}.status 有原始快照时不能为 added")
                if not original.exists():
                    errors.append(f"原始备份不存在：{original}")
                else:
                    expected_hash = tracked.get("originalHash")
                    if not isinstance(expected_hash, str) or not HASH_RE.fullmatch(expected_hash):
                        errors.append(f"{prefix}.originalHash 格式错误")
                    elif hash_bytes(original.read_bytes()) != expected_hash:
                        errors.append(f"原始备份被改写：{relative}")
                if tracked.get("status") == "deleted" and current.exists():
                    errors.append(f"标为删除但源文件仍存在：{relative}")
                if tracked.get("status") != "deleted" and not current.exists():
                    errors.append(f"当前文件不存在：{relative}")
        except ReviewError as exc:
            errors.append(str(exc))
    order = review.get("readingOrder")
    if not isinstance(order, list) or len(order) != len(set(order)) or set(order) != set(ids):
        errors.append("readingOrder 必须且只能包含全部文件 ID，且不能重复")
    file_reviews = review.get("files")
    if not isinstance(file_reviews, list):
        errors.append("review.json.files 必须是数组")
        file_reviews = []
    by_id = {
        item.get("fileId"): item for item in file_reviews if isinstance(item, dict)
    }
    for index, item in enumerate(file_reviews):
        if isinstance(item, dict):
            exact_keys(item, FILE_REVIEW_KEYS, f"review.json.files[{index}]", errors)
    if set(by_id) != set(ids) or len(by_id) != len(file_reviews):
        errors.append("review.json.files 必须且只能包含全部文件")
    total = 0
    for file_id in ids:
        tracked, item = tracked_by_id[file_id], by_id.get(file_id, {})
        actual = item.get("changes", [])
        if not isinstance(actual, list):
            errors.append(f"{tracked['sourcePath']} 的 changes 必须是数组")
            continue
        current, _ = source_file(root, tracked["sourcePath"])
        original = original_file(folder, tracked)
        expected = changes(
            lines(original), lines(current if current.exists() else None), actual
        )
        expected_by_id = {block["id"]: block for block in expected}
        actual_by_id = {
            block.get("id"): block for block in actual if isinstance(block, dict)
        }
        if set(expected_by_id) != set(actual_by_id):
            errors.append(f"{tracked['sourcePath']} 的改动块与真实 diff 不一致，请先 sync")
        total += len(actual)
        for index, block in enumerate(actual):
            if not isinstance(block, dict):
                errors.append(f"{tracked['sourcePath']}#changes[{index}] 必须是对象")
                continue
            prefix = f"{tracked['sourcePath']}#changes[{index}]"
            exact_keys(block, CHANGE_KEYS, prefix, errors)
            expected_block = expected_by_id.get(block.get("id"))
            if expected_block:
                for field in ("kind", "before", "after"):
                    if block.get(field) != expected_block[field]:
                        errors.append(f"{prefix}.{field} 与真实 diff 不一致")
            for range_name in ("before", "after"):
                range_value = block.get(range_name)
                if isinstance(range_value, dict):
                    exact_keys(range_value, RANGE_KEYS, f"{prefix}.{range_name}", errors)
            explain(block.get("title"), f"{prefix}.title", 6, errors)
            explain(
                block.get("originalLogic"), f"{prefix}.originalLogic",
                12 if block.get("kind") == "add" else 30, errors,
            )
            explain(block.get("modifiedLogic"), f"{prefix}.modifiedLogic", 35, errors)
            explain(
                block.get("requirementRelation"), f"{prefix}.requirementRelation", 35, errors
            )
            relation = block.get("requirementRelation")
            if isinstance(relation, str):
                references = set(REQUIREMENT_ID_RE.findall(relation))
                if not relation.lstrip().startswith("[REQ-"):
                    errors.append(
                        f"{prefix}.requirementRelation 必须以 [REQ-xxx] 需求编号开头"
                    )
                if not references:
                    errors.append(f"{prefix}.requirementRelation 必须引用用户需求编号")
                unknown = references - requirement_ids
                if unknown:
                    errors.append(
                        f"{prefix}.requirementRelation 引用了不存在的需求：{', '.join(sorted(unknown))}"
                    )
                valid = references & requirement_ids
                if valid and not valid & leaf_ids:
                    errors.append(
                        f"{prefix}.requirementRelation 只引用了仍有子项的大需求，应继续引用最具体的子需求"
                    )
    if total == 0:
        errors.append("没有检测到任何实际代码改动")
    if errors:
        print(f"校验失败，共 {len(errors)} 个问题：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)
    print(f"校验通过：{folder}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="维护 AI 代码审核包")
    commands = root.add_subparsers(dest="command", required=True)
    create = commands.add_parser("init")
    create.add_argument("change_id")
    create.add_argument("--title", required=True)
    create.add_argument("--source-root")
    create.set_defaults(run=init)
    copy = commands.add_parser("backup")
    copy.add_argument("change_id")
    copy.add_argument("file")
    copy.add_argument("--added", action="store_true")
    copy.add_argument("--source-root")
    copy.set_defaults(run=backup)
    update = commands.add_parser("sync")
    update.add_argument("change_id")
    update.add_argument("--source-root")
    update.set_defaults(run=sync)
    check = commands.add_parser("validate")
    check.add_argument("change_id")
    check.add_argument("--source-root")
    check.set_defaults(run=validate)
    return root


def main() -> None:
    args = parser().parse_args()
    try:
        args.run(args)
    except ReviewError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
