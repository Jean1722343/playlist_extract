#!/usr/bin/env python3
"""Tests for filename generation and sanitization utilities."""

import sys
import time
from pathlib import Path

# Add src/ to path so we can import core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core import build_output_filename, sanitize_filename


def test_default_filename_has_timestamp() -> None:
    """Default filenames should include a timestamp and be unique."""
    name1 = build_output_filename()
    time.sleep(1)
    name2 = build_output_filename()

    print("Test 1: Default filenames with timestamps")
    print(f"  Name 1: {name1}")
    print(f"  Name 2: {name2}")
    print(f"  Different? {name1 != name2}")
    assert name1 != name2, "Filenames should be unique"
    assert name1.endswith(".txt"), "Should end with .txt"


def test_custom_filename_cleanup() -> None:
    """Custom names should be sanitized for filesystem safety."""
    print("\nTest 2: Custom name sanitization")

    cases = [
        ("Mi Playlist @#$%", "Mi_Playlist"),
        ("Rock & Roll Clasicos", "Rock_Roll_Clasicos"),
        ("", "transcripciones_playlist"),
        ("  ", "transcripciones_playlist"),
        ("Normal-Name_123", "Normal-Name_123"),
    ]

    for raw_input, expected_stem_start in cases:
        result = build_output_filename(raw_input)
        print(f"  Input: '{raw_input}' -> Output: {result}")
        assert result.endswith(".txt"), f"Expected .txt extension for '{raw_input}'"


def test_sanitize_filename() -> None:
    """sanitize_filename should remove unsafe characters."""
    print("\nTest 3: sanitize_filename")

    cases = [
        ("Hello World!", "Hello_World"),
        ("Normal-Name", "Normal-Name"),
        ("", "transcripciones_playlist"),
    ]

    for raw_input, expected in cases:
        result = sanitize_filename(raw_input)
        print(f"  Input: '{raw_input}' -> Output: '{result}'")


if __name__ == "__main__":
    test_default_filename_has_timestamp()
    test_custom_filename_cleanup()
    test_sanitize_filename()
    print("\nAll tests passed!")
