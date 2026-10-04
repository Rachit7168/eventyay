"""Helpers for rich-text / HTML field content."""

from __future__ import annotations

import html

from django.utils.html import strip_tags


def is_empty_rich_text(value) -> bool:
    """Return True when value is empty or only whitespace / empty HTML tags."""
    if value is None:
        return True
    text = html.unescape(strip_tags(str(value))).replace('\xa0', ' ').strip()
    return not text
