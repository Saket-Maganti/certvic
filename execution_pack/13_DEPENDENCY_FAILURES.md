# Dependency Failures

Scientific notebooks run with internet disabled and set Hugging Face, Diffusers, datasets, telemetry, and pip offline flags. The only permitted install form is `python -m pip install --no-index --find-links <WHEELHOUSE> -r <LOCK>` after the wheelhouse manifest verifies.

For a missing wheel, rebuild on Linux/CPython 3.10 or provision inside Kaggle; never package a macOS/Windows wheel. For dependency conflicts, compare the selected lock with `configs/runtime/kaggle_t4x2_environment.lock.json`, rebuild the complete wheelhouse, restart the kernel, and rerun 00A. Do not mix preinstalled mismatched packages with a partial wheelhouse.

For Torch/CUDA mismatch, record Python, Torch, torchvision, CUDA runtime, device names, and compute capability from 00A. The target is T4 compute capability 7.5 and the locked Torch/torchvision pair. Unsupported attention kernels must follow the prospective OOM/compatibility ladder; installing from the internet or silently changing model code is prohibited.

Tokenizer, sentencepiece, OpenCV, sklearn, or project import failure blocks before model load. Run `smoke_imports.py` from the wheelhouse bundle and rebuild missing transitive wheels. Keep installation logs in the return ZIP or failure handoff.

