# CertVIC T4×2 Diagnostic-Freeform Fixed Notebooks

These notebooks fix the mechanism/polarity diagnostic parser crash:

- `object_list`
- `describe_then_yes_no`
- any future free-form diagnostic answer format that `certvic.eval.parse.parse_answer` does not support

The fix is intentionally limited to diagnostic runs:

```python
if RUN_TAG in {"mechanism", "polarity"}:
    parsed_answer = raw.strip()
    parse_ok = True
    parse_confidence = 0.0
else:
    raise
```

So spurious and scaled-perception certification-style runs still fail closed if parsing is unsupported.

Use these notebooks for mechanism and polarity runs. They are also safe for spurious/perception_scaled.
