"""Tiny wrapper around Jinja to render the per-agent prompt templates.

Each agent ships a ``prompt.jinja`` file colocated with its ``agent.py``; this
module hides the Environment setup so agents just call ``render``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


_PACKAGE_ROOT: Path = Path(__file__).resolve().parent

_ENV: Environment = Environment(
    loader=FileSystemLoader(str(_PACKAGE_ROOT)),
    autoescape=select_autoescape(enabled_extensions=()),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


def render(template_relpath: str, /, **context: Any) -> str:
    """Render a prompt template, resolved relative to this package's root.

    ``template_relpath`` uses forward slashes, e.g. ``"coding/prompt.jinja"``.
    ``StrictUndefined`` ensures a missing context variable raises instead of
    silently producing an empty hole in the prompt.
    """
    return _ENV.get_template(template_relpath).render(**context)
