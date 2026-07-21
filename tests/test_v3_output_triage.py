"""Tests for the V3 model output / parse triage (prompt 09)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from certvic.eval import output_triage
from certvic.io import write_jsonl
from certvic.reporting import parse_triage_report


def _pred(item_id, variant, raw, parsed, parse_ok=True, provider="qwen2_5_vl_7b", latency=0.5):
    return {
        "run_id": "r1",
        "item_id": item_id,
        "provider_name": provider,
        "provider_type": "open_local",
        "model_name": provider,
        "model_version": "v1",
        "image_variant": variant,
        "prompt": "Is it stable?",
        "raw_output": raw,
        "parsed_answer": parsed,
        "parse_confidence": 1.0 if parse_ok else 0.0,
        "parse_ok": parse_ok,
        "latency_s": latency,
        "timestamp_utc": "2026-06-22T00:00:00+00:00",
    }


def test_clean_run_no_flags(tmp_path):
    preds = []
    for i in range(10):
        preds.append(_pred(f"i{i}", "original", "yes" if i % 2 else "no", "yes" if i % 2 else "no"))
        preds.append(_pred(f"i{i}", "edited", "no" if i % 2 else "yes", "no" if i % 2 else "yes"))
    path = tmp_path / "preds.jsonl"
    write_jsonl(path, preds)
    result = output_triage.triage_outputs(str(path))
    assert result["n_predictions"] == 20
    assert result["any_flags"] is False
    assert result["n_parse_failures"] == 0
    assert result["evidence_claims_made"] is False


def test_parse_failures_detected(tmp_path):
    preds = [_pred(f"i{i}", "original", "maybe?", None, parse_ok=False) for i in range(5)]
    preds += [_pred(f"i{i}", "edited", "yes", "yes") for i in range(5)]
    path = tmp_path / "p.jsonl"
    write_jsonl(path, preds)
    result = output_triage.triage_outputs(str(path))
    assert result["n_parse_failures"] == 5
    stats = result["provider_stats"][0]
    assert stats["high_parse_failure_flag"] is True
    assert "qwen2_5_vl_7b" in result["flagged_providers"]


def test_answer_prior_flag(tmp_path):
    # 19/20 "yes" -> mode answer fraction 0.95 >= 0.9.
    preds = [_pred(f"i{i}", "original", "yes", "yes") for i in range(19)]
    preds.append(_pred("i19", "edited", "no", "no"))
    path = tmp_path / "p.jsonl"
    write_jsonl(path, preds)
    result = output_triage.triage_outputs(str(path))
    assert result["provider_stats"][0]["answer_prior_flag"] is True


def test_degenerate_repeat_flag(tmp_path):
    # Same raw output for all -> degenerate.
    preds = [_pred(f"i{i}", "original", "yes", "yes") for i in range(10)]
    path = tmp_path / "p.jsonl"
    write_jsonl(path, preds)
    result = output_triage.triage_outputs(str(path))
    s = result["provider_stats"][0]
    assert s["degenerate_repeat_flag"] is True
    assert s["top_repeat_fraction"] == 1.0
    # The repeated rows are surfaced as suspicious with the degenerate_repeat reason.
    assert any("degenerate_repeat" in r["reasons"] for r in result["suspicious_outputs"])


def test_refusal_and_long_rationale(tmp_path):
    preds = [
        _pred("i0", "original", "I'm sorry, I cannot determine that from the image.", None, parse_ok=False),
        _pred("i1", "original", "yes " + "because " * 60, "yes"),  # long rationale
        _pred("i2", "original", "no", "no"),
    ]
    path = tmp_path / "p.jsonl"
    write_jsonl(path, preds)
    result = output_triage.triage_outputs(str(path))
    reasons = {r["item_id"]: r["reasons"] for r in result["suspicious_outputs"]}
    assert "refusal" in reasons["i0"]
    assert "long_rationale" in reasons["i1"]
    assert result["provider_stats"][0]["refusal_rate"] > 0


def test_per_provider_split(tmp_path):
    preds = [_pred("i0", "original", "yes", "yes", provider="qwen2_5_vl_7b"),
             _pred("i0", "original", "no", "no", provider="internvl_8b")]
    path = tmp_path / "p.jsonl"
    write_jsonl(path, preds)
    result = output_triage.triage_outputs(str(path))
    providers = {s["provider"] for s in result["provider_stats"]}
    assert providers == {"qwen2_5_vl_7b", "internvl_8b"}


def test_write_outputs_and_report(tmp_path):
    preds = [_pred(f"i{i}", "original", "yes", "yes") for i in range(6)]
    preds += [_pred(f"i{i}", "edited", "no", "no") for i in range(6)]
    path = tmp_path / "p.jsonl"
    write_jsonl(path, preds)
    result = output_triage.triage_outputs(str(path))
    paths = output_triage.write_outputs(result, str(tmp_path / "out"))
    for p in paths.values():
        assert Path(p).exists()
    # provider_output_stats.csv has a header row.
    rows = list(csv.DictReader(Path(paths["provider_stats"]).open(encoding="utf-8")))
    assert rows and "parse_ok_rate" in rows[0]
    report = Path(paths["report"]).read_text(encoding="utf-8")
    assert "Model Output / Parse Triage" in report


def test_report_cli_from_summary(tmp_path):
    preds = [_pred("i0", "original", "yes", "yes")]
    path = tmp_path / "p.jsonl"
    write_jsonl(path, preds)
    result = output_triage.triage_outputs(str(path))
    paths = output_triage.write_outputs(result, str(tmp_path / "out"))
    out_md = tmp_path / "again.md"
    parse_triage_report.main(["--summary", paths["summary"], "--out", str(out_md)])
    assert out_md.exists()


def test_empty_predictions(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    result = output_triage.triage_outputs(str(path))
    assert result["n_predictions"] == 0
    assert result["any_flags"] is False


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
