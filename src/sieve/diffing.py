"""AST-level comparison of TypeScript patches."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import tree_sitter_typescript as tree_sitter_ts
from tree_sitter import Language, Node, Parser


class PatchDivergenceError(ValueError):
    """Raised for an invalid or unparseable patch input."""


@dataclass(frozen=True)
class AstNode:
    """An immutable, normalized representation of a named syntax node."""

    kind: str
    text: str
    children: Sequence[AstNode]


@dataclass(frozen=True)
class _ChangedFile:
    path: PurePosixPath
    ranges: tuple[tuple[int, int], ...]
    deleted: bool


_HUNK = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?:.*)$"
)
_TYPE_SCRIPT_SUFFIXES = {".ts", ".tsx"}
_TYPE_SCRIPT_LANGUAGE = Language(tree_sitter_ts.language_typescript())
_TSX_LANGUAGE = Language(tree_sitter_ts.language_tsx())
_BLOCK_KINDS = {
    "statement_block",
    "class_body",
    "switch_body",
}


def patch_divergence(
    baseline_diff: str,
    perturbed_diff: str,
    baseline_workspace: Path,
    perturbed_workspace: Path,
) -> float:
    """Return normalized tree-edit distance for changed TypeScript blocks.

    Diffs supply only paths and post-image line ranges.  Full files under the
    workspaces are parsed so a truncated hunk is never treated as a program.
    """

    baseline_files = _parse_unified_diff(baseline_diff)
    perturbed_files = _parse_unified_diff(perturbed_diff)
    if not baseline_workspace.is_dir() or not perturbed_workspace.is_dir():
        raise PatchDivergenceError("both workspaces must exist and be directories")

    baseline_typescript = _typescript_files(baseline_files)
    perturbed_typescript = _typescript_files(perturbed_files)
    if bool(baseline_typescript) != bool(perturbed_typescript):
        raise PatchDivergenceError(
            "both patches must contain a TypeScript change, or neither may"
        )

    baseline_trees = _selected_trees(baseline_typescript, baseline_workspace)
    perturbed_trees = _selected_trees(perturbed_typescript, perturbed_workspace)
    distance, larger_size = _forest_distance(baseline_trees, perturbed_trees)
    if larger_size == 0:
        return 0.0
    normalized = distance / larger_size
    if not 0.0 <= normalized <= 1.0:
        raise PatchDivergenceError("normalized tree-edit distance is out of range")
    return normalized


def _parse_unified_diff(diff: str) -> tuple[_ChangedFile, ...]:
    if not diff:
        return ()

    lines = diff.splitlines()
    index = 0
    files: list[_ChangedFile] = []
    saw_file = False
    while index < len(lines):
        line = lines[index]
        if line.startswith("diff --git ") or line.startswith("index "):
            index += 1
            continue
        if not line.startswith("--- "):
            raise PatchDivergenceError("expected a unified-diff old-file header")
        old_path = _header_path(line[4:])
        index += 1
        if index >= len(lines) or not lines[index].startswith("+++ "):
            raise PatchDivergenceError("old-file header is missing a new-file header")
        new_path = _header_path(lines[index][4:])
        index += 1
        saw_file = True
        ranges: list[tuple[int, int]] = []
        saw_hunk = False
        while index < len(lines) and not lines[index].startswith("--- "):
            line = lines[index]
            if line.startswith("diff --git ") or line.startswith("index "):
                break
            match = _HUNK.match(line)
            if match is None:
                raise PatchDivergenceError("invalid unified-diff hunk header")
            saw_hunk = True
            new_start = int(match["new_start"])
            new_count = int(match["new_count"] or "1")
            old_count = int(match["old_count"] or "1")
            index += 1
            old_seen = 0
            new_seen = 0
            while index < len(lines):
                body_line = lines[index]
                if body_line.startswith("@@ ") or body_line.startswith("--- "):
                    break
                if body_line.startswith("diff --git ") or body_line.startswith(
                    "index "
                ):
                    break
                if body_line == "\\ No newline at end of file":
                    index += 1
                    continue
                if not body_line or body_line[0] not in {" ", "+", "-"}:
                    raise PatchDivergenceError("invalid unified-diff hunk body")
                if body_line[0] in {" ", "-"}:
                    old_seen += 1
                if body_line[0] in {" ", "+"}:
                    new_seen += 1
                index += 1
            if old_seen != old_count or new_seen != new_count:
                raise PatchDivergenceError("unified-diff hunk line counts do not match")
            ranges.append((new_start, max(new_count, 1)))
        if not saw_hunk:
            raise PatchDivergenceError("unified-diff file entry has no hunk")
        selected_path = new_path if new_path is not None else old_path
        if selected_path is None:
            raise PatchDivergenceError("unified-diff file entry has no usable path")
        files.append(
            _ChangedFile(
                path=selected_path,
                ranges=tuple(ranges),
                deleted=new_path is None,
            )
        )
    if not saw_file:
        raise PatchDivergenceError("input is not a unified diff")
    return tuple(files)


def _header_path(header: str) -> PurePosixPath | None:
    raw_path = header.split("\t", maxsplit=1)[0]
    if raw_path == "/dev/null":
        return None
    if raw_path.startswith(("a/", "b/")):
        raw_path = raw_path[2:]
    path = PurePosixPath(raw_path)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PatchDivergenceError("unified-diff path is unsafe")
    return path


def _typescript_files(files: Iterable[_ChangedFile]) -> tuple[_ChangedFile, ...]:
    return tuple(item for item in files if item.path.suffix in _TYPE_SCRIPT_SUFFIXES)


def _selected_trees(
    changed_files: Iterable[_ChangedFile], workspace: Path
) -> dict[PurePosixPath, tuple[AstNode, ...]]:
    selected: dict[PurePosixPath, tuple[AstNode, ...]] = {}
    for changed_file in changed_files:
        if changed_file.deleted:
            selected[changed_file.path] = ()
            continue
        source_path = workspace.joinpath(*changed_file.path.parts)
        if not source_path.is_file():
            raise PatchDivergenceError(
                f"changed TypeScript path is absent from workspace: {changed_file.path}"
            )
        source = source_path.read_bytes()
        tree = _parser_for(changed_file.path).parse(source)
        if tree.root_node.has_error:
            raise PatchDivergenceError(
                f"TypeScript source could not be parsed: {changed_file.path}"
            )
        nodes = _enclosing_nodes(tree.root_node, changed_file.ranges)
        selected[changed_file.path] = tuple(
            _to_ast_node(node, source) for node in nodes
        )
    return selected


def _parser_for(path: PurePosixPath) -> Parser:
    language = _TSX_LANGUAGE if path.suffix == ".tsx" else _TYPE_SCRIPT_LANGUAGE
    return Parser(language)


def _enclosing_nodes(root: Node, ranges: Iterable[tuple[int, int]]) -> tuple[Node, ...]:
    selected: list[Node] = []
    seen: set[tuple[str, tuple[int, int], tuple[int, int]]] = set()
    for start_line, line_count in ranges:
        node = _smallest_enclosing_node(
            root, start_line - 1, start_line - 1 + line_count
        )
        identity = (node.type, node.start_point, node.end_point)
        if identity not in seen:
            seen.add(identity)
            selected.append(node)
    selected.sort(key=lambda node: (node.start_byte, node.end_byte, node.type))
    return tuple(selected)


def _smallest_enclosing_node(root: Node, start_row: int, end_row: int) -> Node:
    candidates: list[Node] = []

    def visit(node: Node) -> None:
        if node.start_point[0] <= start_row and node.end_point[0] >= end_row:
            if node.type in _BLOCK_KINDS or "function" in node.type:
                candidates.append(node)
            for child in node.named_children:
                visit(child)

    visit(root)
    if candidates:
        return min(
            candidates,
            key=lambda node: (
                node.end_byte - node.start_byte,
                node.start_byte,
                node.type,
            ),
        )
    return root


def _to_ast_node(node: Node, source: bytes) -> AstNode:
    children = tuple(_to_ast_node(child, source) for child in node.named_children)
    text = "" if children else source[node.start_byte : node.end_byte].decode("utf-8")
    return AstNode(kind=node.type, text=text, children=children)


def _forest_distance(
    baseline: dict[PurePosixPath, tuple[AstNode, ...]],
    perturbed: dict[PurePosixPath, tuple[AstNode, ...]],
) -> tuple[int, int]:
    distance = 0
    larger_size = 0
    for path in sorted(set(baseline) | set(perturbed), key=str):
        baseline_nodes = baseline.get(path, ())
        perturbed_nodes = perturbed.get(path, ())
        larger_size += max(
            sum(_node_count(node) for node in baseline_nodes),
            sum(_node_count(node) for node in perturbed_nodes),
        )
        distance += _sequence_distance(baseline_nodes, perturbed_nodes)
    return distance, larger_size


def _sequence_distance(left: Sequence[AstNode], right: Sequence[AstNode]) -> int:
    table = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    for left_index, node in enumerate(left, start=1):
        table[left_index][0] = table[left_index - 1][0] + _node_count(node)
    for right_index, node in enumerate(right, start=1):
        table[0][right_index] = table[0][right_index - 1] + _node_count(node)
    for left_index, left_node in enumerate(left, start=1):
        for right_index, right_node in enumerate(right, start=1):
            table[left_index][right_index] = min(
                table[left_index - 1][right_index] + _node_count(left_node),
                table[left_index][right_index - 1] + _node_count(right_node),
                table[left_index - 1][right_index - 1]
                + _tree_distance(left_node, right_node),
            )
    return table[-1][-1]


def _tree_distance(left: AstNode, right: AstNode) -> int:
    if _fully_disjoint(left, right):
        return max(_node_count(left), _node_count(right))
    root_cost = int(left.kind != right.kind or left.text != right.text)
    return root_cost + _sequence_distance(left.children, right.children)


def _node_count(node: AstNode) -> int:
    return 1 + sum(_node_count(child) for child in node.children)


def _fully_disjoint(left: AstNode, right: AstNode) -> bool:
    """Whether two selections have no common semantic AST node.

    Common program and block wrappers are deliberately excluded: they identify
    location, rather than a shared code construct.  This realizes the §7.1
    ``1.0 = fully disjoint changes`` rule for, for example, return versus
    throw bodies.
    """

    left_signatures = _semantic_signatures(left)
    right_signatures = _semantic_signatures(right)
    return bool(
        left_signatures and right_signatures and not left_signatures & right_signatures
    )


def _semantic_signatures(node: AstNode) -> set[tuple[str, str]]:
    ignored = {"program", "statement_block", "class_body", "switch_body"}
    signatures: set[tuple[str, str]] = set()
    if node.kind not in ignored:
        signatures.add((node.kind, node.text))
    for child in node.children:
        signatures.update(_semantic_signatures(child))
    return signatures
