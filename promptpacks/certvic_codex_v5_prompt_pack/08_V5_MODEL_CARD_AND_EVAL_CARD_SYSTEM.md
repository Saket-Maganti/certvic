# CertVIC V5 Prompt — Model Card and Eval Card System

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Build model/eval cards for every future run.

Create:
- `certvic/cards/model_card.py`
- `certvic/cards/eval_card.py`

CLI:
`python3 -m certvic.cards.model_card --provider <provider> --out cards/model_<provider>.md`
`python3 -m certvic.cards.eval_card --run-dir <run_dir> --out cards/eval_<run_id>.md`

Model card fields:
- provider
- model id
- license/status
- open/local/free status
- expected memory
- quantization
- prompt settings
- limitations

Eval card fields:
- tasks
- model card
- predictions
- parser
- scoring
- claim status
- provenance

Tests:
- cards generated
- paid/provider unknown flagged
- missing license flagged
- no evidence from incomplete eval card

Docs:
- `docs/V5_MODEL_EVAL_CARDS_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
