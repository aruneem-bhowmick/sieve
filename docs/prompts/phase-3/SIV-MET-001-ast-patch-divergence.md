# SIV-MET-001 — AST-level patch divergence

## Traceability

- Phase: 3 — Scoring & Diffing (SIEVE-SPEC.md §13)
- Requirement: AST-level patch divergence (§7.1) via tree-sitter
- Wave: 1
- Depends on: Phase 2
- Unblocks: SIV-MET-003, SIV-OPS-002
- Advances DoD: supplies the normalized patch-divergence value the score CLI
  must persist.

## Objective

Implement the Layer 3 structural patch metric. It uses the baseline and
perturbed `TraceRecord.final_diff` values to locate changes, then parses the
complete persisted TypeScript workspace files to compare enclosing changed
functions or blocks. It never treats raw diff text as the artifact being
scored and returns a stable number in `[0.0, 1.0]`.

## Context & assumptions

- Read `_PREAMBLE.md` first; inherit its contracts, standards, and taxonomy.
- Read `TraceRecord.final_diff` to identify changed TypeScript paths and
  post-image line ranges. Read each run's persisted `workspace/` files for
  syntax-tree construction; do not change trace persistence.
- Phase 2 has valid recorded TypeScript trace pairs. The Phase 3 score runner
  does not exist yet and is owned by SIV-MET-003.
- Risk §15: “AST diffing is noisy/non-normalized, making patch divergence
  meaningless.” Use a deterministic tree-edit distance and let SIV-OPS-002
  freeze known distances.

## Interface specification

```python
# src/sieve/diffing.py
class PatchDivergenceError(ValueError):
    """Raised for an invalid or unparseable patch input."""
    pass

@dataclass(frozen=True)
class AstNode:
    kind: str
    text: str
    children: Sequence["AstNode"]

def patch_divergence(
    baseline_diff: str,
    perturbed_diff: str,
    baseline_workspace: Path,
    perturbed_workspace: Path,
) -> float:
    pass
```

`patch_divergence` must parse TypeScript `.ts` and `.tsx` unified diffs
only to obtain changed relative paths and post-image line ranges. For every
changed TypeScript path, read the complete post-image source from the
corresponding workspace, parse it with the TypeScript tree-sitter grammar,
and select the smallest named function or block enclosing each changed range.
Pair selected blocks by relative path and source order, compute an ordered
tree-edit distance with unit insert/delete/substitute cost, and divide by the
larger selected-tree node count. Return `0.0` for two empty or structurally
identical selections and `1.0` when exactly one selection is empty or
selected trees are fully disjoint. A file deleted from a final workspace is
an empty selection, not a missing-workspace error. Raise
`PatchDivergenceError` for malformed unified diffs, a missing workspace, a
changed post-image TypeScript path absent from its workspace, an unparseable
complete TypeScript source file, or a normalized value outside the range.
Ignore non-TypeScript changed files; reject a pair with no TypeScript change
on only one side.

## Files to create or modify

- **Reads:** `SIEVE-SPEC.md` — §7.1 binding algorithm and normalization.
- **Reads:** `tests/fixtures/phase1/SIEVE-T1-baseline-trace.json` —
  representative final diff for test inputs.
- **Reads:** `tests/fixtures/phase2/SIEVE-T1-int01-perturbed-trace.json` —
  identical-patch fixture.
- **Writes (creates or modifies):** `pyproject.toml` — add compatible
  `tree-sitter` and `tree-sitter-typescript` runtime dependencies.
- **Writes (creates or modifies):** `src/sieve/diffing.py` — parser,
  normalized immutable tree representation, and distance function.
- **Writes (creates or modifies):** `tests/test_diffing.py` — focused
  unit and normalization tests.

## Implementation notes

Use the grammar package’s TypeScript language object; do not use textual
similarity, a regular-expression token metric, a JavaScript subprocess, or a
synthetic wrapper around a truncated diff hunk. Preserve grammar node kinds
and leaf source text in `AstNode` so a changed identifier, literal, operator,
or template prefix changes the tree. Pair changed blocks by normalized path
and source order; unmatched blocks are insertions or deletions. Make source
ordering and tree traversal deterministic.

The §7.1 rule is: “Tree-edit-distance over `ast`/`tree-sitter` parse
trees, normalized by tree size.” A formatter-only whitespace change must
therefore produce `0.0` after parsing.

## Test specification

| Type | Test cases |
|---|---|
| Unit | `test_identical_typescript_patch_has_zero_divergence`; `test_whitespace_only_function_formatting_has_zero_divergence`; `test_disjoint_return_expression_has_divergence_one`; `test_changed_identifier_or_literal_has_positive_divergence`; `test_hunk_without_enclosing_function_boundaries_uses_complete_workspace_source`; `test_malformed_hunk_or_missing_workspace_raises_patch_divergence_error`. |
| Integration | N/A — this primitive has no Layer 2/3 handoff until SIV-MET-003 consumes it. |
| System | N/A — a complete baseline/intervention-to-score pipeline is owned by SIV-MET-003. |
| Acceptance | N/A — the executable Phase 3 DoD assertion is owned by SIV-MET-003. |
| Smoke | `test_patch_divergence_smoke_phase2_t1_int01_workspaces_are_zero` loads the Phase 1 baseline and Phase 2 perturbed final diffs plus complete workspace snapshots and returns `0.0`. |
| Sanity | `test_divergence_is_bounded_and_orders_identical_less_than_changed_less_than_disjoint` asserts values are in range and that the known identical, one-expression-change, and disjoint cases are ordered; `test_multiple_changed_typescript_files_pair_by_path_and_source_order` prevents nondeterministic block pairing. |
| Regression | N/A — SIV-OPS-002 owns committed golden pair distances and the CI regression gate. |
| End-to-end | N/A — this requirement exposes no CLI; SIV-MET-003 adds `sieve score`. |
| API | N/A — AST parsing makes no Codex/GPT-5.6 API request. |
| UI | N/A — the static report is Phase 4 scope. |

## Definition of done for this prompt

- [ ] The declared interfaces parse TypeScript diff hunks through tree-sitter
  and return the specified normalized values.
- [ ] All non-N/A tests pass via `python -m pytest -v tests/test_diffing.py`.
- [ ] `python -m ruff check .`, `python -m black --check .`, and
  `python -m mypy --strict .` pass.
- [ ] No §5 data contract is changed.
- [ ] SIV-OPS-002 can use this stable function without duplicating its logic.
