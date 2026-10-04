"""Helpers for rich-text / HTML field content."""

from __future__ import annotations

import html
import re

from django.utils.html import strip_tags

# Zero-width / format characters that look empty but survive str.strip().
_INVISIBLE_CHARS_RE = re.compile(
    '[\u200b\u200c\u200d\u2060\ufeff\u00ad]'
)


def is_empty_rich_text(value) -> bool:
    """Return True when value is empty or only whitespace / empty HTML tags."""
    if value is None:
        return True
    text = html.unescape(strip_tags(str(value)))
    text = _INVISIBLE_CHARS_RE.sub('', text).replace('\xa0', ' ').strip()
    return not text
