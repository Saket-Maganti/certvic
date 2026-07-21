"""Scale and free-compute budget planning for CertVIC (V3).

Estimates the CPU / GPU / human / wall-clock / storage cost of 200/1k/2k studies
under free Kaggle/Colab limits, identifies the bottleneck, and recommends
per-session batch sizes. Planning only: no inference, no downloads, no paid
services, no evidence claims. Estimates are deliberately conservative.
"""
