"""Small valid-ipynb builders used by V4 notebook generators."""

from __future__ import annotations

import json
from pathlib import Path


ZERO_COST_WARNING = (
    "CertVIC zero-cost policy: do not add paid APIs, credentials, surprise downloads, "
    "or paper claims. Use only user-mounted datasets and user-managed model caches."
)


def markdown_cell(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(text)}


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _lines(source),
    }


def make_notebook(title: str, cells: list[dict]) -> dict:
    return {
        "cells": [markdown_cell(f"# {title}\n\n{ZERO_COST_WARNING}"), *cells],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write_notebook(path: str | Path, notebook: dict) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(notebook, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def checklist(title: str, items: list[str]) -> str:
    return "\n".join([f"# {title}", "", *[f"- [ ] {item}" for item in items], ""])


def _lines(text: str) -> list[str]:
    return [line + "\n" for line in text.strip().splitlines()]

