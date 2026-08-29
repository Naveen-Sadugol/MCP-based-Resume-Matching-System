import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from filesystem_mcp_server import (
    BASE_DIR,
    batch_process,
    list_files,
    read_file,
    write_file,
)


def test_list_files_contains_sample_resumes():
    items = list_files("resumes")

    names = {item["name"] for item in items}

    assert "alice_backend.txt" in names


def test_batch_process_reads_resumes():
    result = batch_process("resumes", "*.txt")

    assert result["count"] >= 3
    assert all("content" in item for item in result["files"])


def test_path_traversal_is_blocked():
    with pytest.raises(ValueError):
        read_file("../outside.txt")


def test_write_file_creates_file():
    target = "test_output.txt"

    result = write_file(target, "hello")

    assert result["status"] == "ok"

    assert (
        BASE_DIR / target
    ).read_text(encoding="utf-8") == "hello"

    (BASE_DIR / target).unlink(missing_ok=True)