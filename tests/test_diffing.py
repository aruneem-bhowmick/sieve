from __future__ import annotations

import json
from pathlib import Path

import pytest

from sieve.diffing import PatchDivergenceError, patch_divergence


def _diff(path: str, old: str, new: str) -> str:
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    return "\n".join(
        [
            f"--- a/{path}",
            f"+++ b/{path}",
            f"@@ -1,{len(old_lines)} +1,{len(new_lines)} @@",
            *(f"-{line}" for line in old_lines),
            *(f"+{line}" for line in new_lines),
            "",
        ]
    )


def _workspace(root: Path, **files: str) -> Path:
    workspace = root / "workspace"
    for relative_path, source in files.items():
        target = workspace / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    return workspace


def test_identical_typescript_patch_has_zero_divergence(tmp_path: Path) -> None:
    source = "export function value(): number {\n  return 1;\n}\n"
    diff = _diff("src/value.ts", source, source)
    baseline = _workspace(tmp_path / "baseline", **{"src/value.ts": source})
    perturbed = _workspace(tmp_path / "perturbed", **{"src/value.ts": source})

    assert patch_divergence(diff, diff, baseline, perturbed) == 0.0


def test_whitespace_only_function_formatting_has_zero_divergence(
    tmp_path: Path,
) -> None:
    compact = "export function value(): number { return 1; }\n"
    formatted = "export function value(): number {\n  return 1;\n}\n"
    baseline = _workspace(tmp_path / "baseline", **{"src/value.ts": compact})
    perturbed = _workspace(tmp_path / "perturbed", **{"src/value.ts": formatted})

    assert (
        patch_divergence(
            _diff("src/value.ts", compact, compact),
            _diff("src/value.ts", compact, formatted),
            baseline,
            perturbed,
        )
        == 0.0
    )


def test_disjoint_return_expression_has_divergence_one(tmp_path: Path) -> None:
    baseline_source = "export function value() {\n  return 1;\n}\n"
    perturbed_source = "export function value() {\n  throw new Error('no');\n}\n"
    baseline = _workspace(tmp_path / "baseline", **{"src/value.ts": baseline_source})
    perturbed = _workspace(tmp_path / "perturbed", **{"src/value.ts": perturbed_source})

    assert (
        patch_divergence(
            (
                "--- a/src/value.ts\n+++ b/src/value.ts\n@@ -2 +2 @@\n"
                "-  return 1;\n+  return 1;\n"
            ),
            (
                "--- a/src/value.ts\n+++ b/src/value.ts\n@@ -2 +2 @@\n"
                "-  throw new Error('no');\n+  throw new Error('no');\n"
            ),
            baseline,
            perturbed,
        )
        == 1.0
    )


def test_changed_identifier_or_literal_has_positive_divergence(tmp_path: Path) -> None:
    baseline_source = "export function value() {\n  return total;\n}\n"
    perturbed_source = "export function value() {\n  return count;\n}\n"
    baseline = _workspace(tmp_path / "baseline", **{"src/value.ts": baseline_source})
    perturbed = _workspace(tmp_path / "perturbed", **{"src/value.ts": perturbed_source})

    assert (
        0.0
        < patch_divergence(
            _diff("src/value.ts", "", baseline_source),
            _diff("src/value.ts", "", perturbed_source),
            baseline,
            perturbed,
        )
        < 1.0
    )


def test_hunk_without_enclosing_function_boundaries_uses_complete_workspace_source(
    tmp_path: Path,
) -> None:
    baseline_source = (
        "export function value() {\n  const result = 1;\n  return result;\n}\n"
    )
    perturbed_source = (
        "export function value() {\n  const result = 2;\n  return result;\n}\n"
    )
    hunk = (
        "--- a/src/value.ts\n+++ b/src/value.ts\n@@ -2 +2 @@\n"
        "-  const result = 1;\n+  const result = 2;\n"
    )
    baseline = _workspace(tmp_path / "baseline", **{"src/value.ts": baseline_source})
    perturbed = _workspace(tmp_path / "perturbed", **{"src/value.ts": perturbed_source})

    assert 0.0 < patch_divergence(hunk, hunk, baseline, perturbed) < 1.0


def test_malformed_hunk_or_missing_workspace_raises_patch_divergence_error(
    tmp_path: Path,
) -> None:
    source = "export const value = 1;\n"
    valid_diff = _diff("src/value.ts", source, source)
    workspace = _workspace(tmp_path, **{"src/value.ts": source})

    with pytest.raises(PatchDivergenceError, match="unified"):
        patch_divergence("not a diff", valid_diff, workspace, workspace)
    with pytest.raises(PatchDivergenceError, match="workspaces"):
        patch_divergence(valid_diff, valid_diff, tmp_path / "missing", workspace)


def test_patch_divergence_smoke_phase2_t1_int01_workspaces_are_zero(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parent / "fixtures"
    baseline_trace = json.loads(
        (root / "phase1" / "SIEVE-T1-baseline-trace.json").read_text(encoding="utf-8")
    )
    perturbed_trace = json.loads(
        (root / "phase2" / "SIEVE-T1-int01-perturbed-trace.json").read_text(
            encoding="utf-8"
        )
    )
    source = (
        "export function normalizeName(name?: string): string {\n"
        '  return name?.trim() ?? "";\n}\n'
    )
    baseline = _workspace(tmp_path / "baseline", **{"src/normalizeName.ts": source})
    perturbed = _workspace(tmp_path / "perturbed", **{"src/normalizeName.ts": source})

    assert (
        patch_divergence(
            baseline_trace["final_diff"],
            perturbed_trace["final_diff"],
            baseline,
            perturbed,
        )
        == 0.0
    )


def test_divergence_is_bounded_and_orders_identical_less_than_changed_less_than_disjoint(  # noqa: E501
    tmp_path: Path,
) -> None:
    identical = "export function value() {\n  return 1;\n}\n"
    changed = "export function value() {\n  return 2;\n}\n"
    disjoint = "export function value() {\n  throw new Error('no');\n}\n"
    baseline = _workspace(tmp_path / "baseline", **{"src/value.ts": identical})
    changed_workspace = _workspace(tmp_path / "changed", **{"src/value.ts": changed})
    disjoint_workspace = _workspace(tmp_path / "disjoint", **{"src/value.ts": disjoint})
    baseline_diff = _diff("src/value.ts", "", identical)
    values = (
        patch_divergence(baseline_diff, baseline_diff, baseline, baseline),
        patch_divergence(
            baseline_diff,
            _diff("src/value.ts", "", changed),
            baseline,
            changed_workspace,
        ),
        patch_divergence(
            baseline_diff,
            _diff("src/value.ts", "", disjoint),
            baseline,
            disjoint_workspace,
        ),
    )

    assert all(0.0 <= value <= 1.0 for value in values)
    assert values[0] < values[1] < values[2]


def test_multiple_changed_typescript_files_pair_by_path_and_source_order(
    tmp_path: Path,
) -> None:
    baseline_one = "export function one() {\n  return 1;\n}\n"
    baseline_two = "export function two() {\n  return 2;\n}\n"
    baseline_view = "export function View() {\n  return <p>one</p>;\n}\n"
    perturbed_one = "export function one() {\n  return 3;\n}\n"
    perturbed_two = "export function two() {\n  return 4;\n}\n"
    perturbed_view = "export function View() {\n  return <p>two</p>;\n}\n"
    baseline = _workspace(
        tmp_path / "baseline",
        **{
            "src/one.ts": baseline_one,
            "src/two.ts": baseline_two,
            "src/view.tsx": baseline_view,
        },
    )
    perturbed = _workspace(
        tmp_path / "perturbed",
        **{
            "src/one.ts": perturbed_one,
            "src/two.ts": perturbed_two,
            "src/view.tsx": perturbed_view,
        },
    )
    baseline_diff = (
        _diff("src/two.ts", "", baseline_two)
        + _diff("src/view.tsx", "", baseline_view)
        + _diff("src/one.ts", "", baseline_one)
    )
    perturbed_diff = (
        _diff("src/one.ts", "", perturbed_one)
        + _diff("src/two.ts", "", perturbed_two)
        + _diff("src/view.tsx", "", perturbed_view)
    )

    first = patch_divergence(baseline_diff, perturbed_diff, baseline, perturbed)
    second = patch_divergence(baseline_diff, perturbed_diff, baseline, perturbed)
    assert 0.0 < first < 1.0
    assert first == second
