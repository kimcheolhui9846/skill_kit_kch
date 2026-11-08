"""Compatibility shim: the block merge now lives in kit.writers.markdown_block (P3-T2)."""

from __future__ import annotations

from .writers.markdown_block import BEGIN, END, MarkerError, extract_block, merge, render_block

__all__ = ["BEGIN", "END", "MarkerError", "extract_block", "merge", "render_block"]
