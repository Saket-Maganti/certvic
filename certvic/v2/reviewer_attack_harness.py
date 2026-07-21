"""Reviewer attack harness (V2.5).

``docs/REVIEWER_ATTACKS_AND_DEFENSES.md`` lists the objections a harsh CVPR
reviewer will raise. Prose is not a defense. This harness binds each attack to a
*live, executable* check that either runs the defense tooling or asserts the
defense artifact exists, so "we have a defense" is verifiable, not aspirational.

Each attack is classified as:

* ``blocking``     - a core defense that must be tooling-ready before real runs.
* ``enhancement``  - a hardening item tracked on the roadmap; not yet a gate.

The harness reports, per attack, whether the defense *tooling is ready* (the
machinery runs today on synthetic input) and, where relevant, whether a defense
*artifact is present* (produced post-run). It runs no models and makes no claims.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _safe(fn) -> tuple[bool, str]:
    """Run a check fn returning (ready, note); never raise."""
    try:
        return fn()
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"check raised: {exc}"


# --- individual defense checks -------------------------------------------------

def _check_edit_realism() -> tuple[bool, str]:
    from certvic.edit.diffusion_preflight import diffusion_preflight  # noqa: F401
    from certvic.edit.quality_gates import evaluate_edit_quality  # noqa: F401
    from certvic.validation.export_visual_review import main as _  # noqa: F401

    return True, "quality gates + diffusion preflight + visual-review export are importable"


def _check_no_causal_claim() -> tuple[bool, str]:
    from certvic.validation.claims import validate_claim_text

    errs = validate_claim_text("This proves causal understanding in all vlms", certified=True, has_cs_lower_bound=True)
    return (len(errs) >= 2), f"forbidden-phrase gate fires ({len(errs)} errors on a causal overclaim)"


def _check_small_scale() -> tuple[bool, str]:
    from certvic.metrics.confseq_wrappers import gap_cs

    g = gap_cs([1] * 30, [0] * 30, backend="auto")
    return bool(g.get("available")), f"anytime-valid CS available at n=30 (method={g.get('method')})"


def _check_label_ambiguity() -> tuple[bool, str]:
    from certvic.data import label_policy  # noqa: F401

    return True, "ADE20K label policy module is importable"


def _check_licensing() -> tuple[bool, str]:
    from certvic.release.build_artifact import main as _  # noqa: F401
    from certvic.validation import zero_cost  # noqa: F401

    return True, "recipe-first release builder + zero-cost audit are importable"


def _check_only_open_models() -> tuple[bool, str]:
    from certvic.providers.registry import PAID_PROVIDER_NAMES

    return (PAID_PROVIDER_NAMES == set()), f"no paid providers registered (PAID_PROVIDER_NAMES={sorted(PAID_PROVIDER_NAMES)})"


def _check_optional_stopping() -> tuple[bool, str]:
    from certvic.sim.anytime_validity import run_anytime_validity_lab

    with tempfile.TemporaryDirectory() as tmp:
        result = run_anytime_validity_lab(tmp, n=150, n_trials=600, alpha=0.05, threshold=0.0, seed=0)
    checks = result["checks"]
    ready = checks["cs_type_i_controlled"] and checks["peeking_fixed_n_inflates_type_i"]
    return ready, "validity lab: CS controls Type-I under peeking; peeked fixed-n inflates"


def _check_gameable_without_vision() -> tuple[bool, str]:
    from certvic.eval.adversarial_audit import run_adversarial_audit  # noqa: F401
    from certvic.eval.ablation_baselines import BASELINES

    return True, f"adversarial audit + {len(BASELINES)} construct-validity baselines available"


def _check_parser_sensitivity() -> tuple[bool, str]:
    from certvic.metrics.summary import summarize_pair_scores

    summary = summarize_pair_scores([])
    return ("parse_failure_sensitivity" in summary), "summary exposes parser-sensitivity buckets"


def _check_fabricated_numbers() -> tuple[bool, str]:
    from certvic.validation.paper_numbers_guard import verify_paper

    result = verify_paper(repo_root=REPO_ROOT)
    return bool(result["passed"]), f"paper number-provenance guard passes ({result['n_violations']} violations)"


def _check_multiplicity() -> tuple[bool, str]:
    doc = REPO_ROOT / "docs/PRE_REGISTRATION.md"
    if not doc.exists():
        return False, "docs/PRE_REGISTRATION.md missing (primary endpoint + multiplicity policy)"
    text = doc.read_text(encoding="utf-8").lower()
    ok = "primary endpoint" in text and ("multiplic" in text or "subgroup" in text)
    return ok, "pre-registration declares a primary endpoint and a multiplicity policy"


def _check_clustering() -> tuple[bool, str]:
    doc = REPO_ROOT / "docs/PRE_REGISTRATION.md"
    if not doc.exists():
        return False, "pre-registration missing; clustering/independence policy undocumented"
    text = doc.read_text(encoding="utf-8").lower()
    ok = "cluster" in text or "per-source" in text or "independence" in text
    return ok, "clustering/independence policy documented (per-source aggregation diagnostic still on roadmap)"


ATTACKS = [
    {"id": "edits_not_photorealistic", "kind": "blocking", "fn": _check_edit_realism,
     "attack": "The edits are fake / not photorealistic."},
    {"id": "not_causal_understanding", "kind": "blocking", "fn": _check_no_causal_claim,
     "attack": "This isn't about causal understanding."},
    {"id": "scale_too_small", "kind": "blocking", "fn": _check_small_scale,
     "attack": "The scale is too small."},
    {"id": "labels_ambiguous", "kind": "blocking", "fn": _check_label_ambiguity,
     "attack": "Labels are ambiguous."},
    {"id": "licensing", "kind": "blocking", "fn": _check_licensing,
     "attack": "Licensing of released data."},
    {"id": "only_open_models", "kind": "blocking", "fn": _check_only_open_models,
     "attack": "Only open models were tested."},
    {"id": "optional_stopping_invalidates", "kind": "blocking", "fn": _check_optional_stopping,
     "attack": "Optional stopping invalidates the statistics."},
    {"id": "gameable_without_vision", "kind": "blocking", "fn": _check_gameable_without_vision,
     "attack": "The task is gameable without vision."},
    {"id": "parser_hides_failures", "kind": "blocking", "fn": _check_parser_sensitivity,
     "attack": "Parser choices hide failures."},
    {"id": "fabricated_numbers", "kind": "blocking", "fn": _check_fabricated_numbers,
     "attack": "The reported numbers could be fabricated / hand-entered."},
    {"id": "multiplicity_subgroup_mining", "kind": "enhancement", "fn": _check_multiplicity,
     "attack": "You mined subgroups until one looked bad (multiple comparisons)."},
    {"id": "item_dependence_clustering", "kind": "enhancement", "fn": _check_clustering,
     "attack": "Items from the same source image are correlated; effective n is inflated."},
]


def run_reviewer_attack_harness() -> dict:
    rows = []
    for attack in ATTACKS:
        ready, note = _safe(attack["fn"])
        rows.append(
            {
                "id": attack["id"],
                "attack": attack["attack"],
                "kind": attack["kind"],
                "tooling_ready": ready,
                "note": note,
            }
        )
    blocking_unready = [r for r in rows if r["kind"] == "blocking" and not r["tooling_ready"]]
    enhancement_unready = [r for r in rows if r["kind"] == "enhancement" and not r["tooling_ready"]]
    return {
        "harness": "reviewer_attack_harness",
        "passed": not blocking_unready,
        "n_attacks": len(rows),
        "n_blocking_ready": sum(1 for r in rows if r["kind"] == "blocking" and r["tooling_ready"]),
        "n_blocking": sum(1 for r in rows if r["kind"] == "blocking"),
        "blocking_unready": [r["id"] for r in blocking_unready],
        "enhancement_unready": [r["id"] for r in enhancement_unready],
        "attacks": rows,
        "evidence_claims_made": False,
    }


def render_report(result: dict) -> str:
    status = "PASS" if result["passed"] else "FAIL"
    lines = [
        "# Reviewer Attack Harness (V2.5)",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Overall: **{status}** - {result['n_blocking_ready']}/{result['n_blocking']} blocking defenses tooling-ready.",
        "",
        "Each known reviewer attack is bound to a live, executable defense check.",
        "`blocking` defenses must be ready before real runs; `enhancement` items are",
        "tracked on the roadmap.",
        "",
        "| Attack | Kind | Tooling ready | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for r in result["attacks"]:
        mark = "ready" if r["tooling_ready"] else "PENDING"
        note = r["note"].replace("|", "/")
        lines.append(f"| {r['attack']} | {r['kind']} | {mark} | {note} |")
    lines += [
        "",
        "Tooling-ready means the defense machinery runs today; it does not by itself",
        "constitute empirical evidence. Post-run, each defense must also emit its",
        "artifact (e.g. the construct-validity table, the certification trajectory).",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC reviewer attack harness (V2.5)")
    parser.add_argument("--out", default="docs/REVIEWER_ATTACK_HARNESS_REPORT.md")
    parser.add_argument("--json-out")
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args(argv)
    result = run_reviewer_attack_harness()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "blocking_unready": result["blocking_unready"], "enhancement_unready": result["enhancement_unready"]}, sort_keys=True))
    if not result["passed"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
