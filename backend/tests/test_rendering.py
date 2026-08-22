import pytest

from app.rendering import escape_drawtext, format_seconds


def test_drawtext_escapes_shell_filter_characters():
    assert escape_drawtext("50% of: it's") == "50\\% of\\: it\\'s"


def test_milliseconds_format_for_ffmpeg():
    assert format_seconds(1500) == "1.500"
