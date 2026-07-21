# Snapshot provisioning handoff

Open `notebooks/kaggle/provisioning/01_build_certvic_model_snapshot_parameterized.ipynb` with Internet
on and accelerator off. Execute it three times with `PROVIDER` exactly `qwen2_5_vl_7b`, `internvl_8b`,
and `llava_onevision_7b`. Download, without renaming, `qwen2_5_vl_7b_snapshot.zip`,
`internvl2_8b_snapshot.zip`, and `llava_onevision_7b_snapshot.zip` to
`kaggle_uploads/02_snapshots/`. Validate each with `python3 -m certvic.cvpr.kaggle_bundle verify <ZIP>`;
then run `python3 scripts/run_all_cpu_workflows.py --resume`. The exact immutable revisions are Qwen
`cc594898137f460bfe9f0759e9844b3ce807cfb5`, InternVL
`6fb9ad6924f69424e57fab2ab061d707688f0296`, and LLaVA
`0d50680527681998e456c7b78950205bedd8a068`; model, processor, and tokenizer must remain on the
provider's same listed commit (including InternVL remote code).
