"""
MCP filesystem server for the Resume Matching project.

The official MCP Python SDK implements the MCP protocol and JSON-RPC 2.0
transport details for us. This file focuses on the application capabilities:
filesystem tools, resources, directory watching, and batch processing.

Run:
    python filesystem_mcp_server.py
or:
    python filesystem_mcp_server.py --transport streamable-http
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

BASE_DIR = Path(os.getenv("RESUME_BASE_DIR", "./data")).resolve()
RESUME_DIR = BASE_DIR / "resumes"
OUTPUT_DIR = BASE_DIR / "output"

RESUME_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

mcp = FastMCP(
    "ResumeFileSystem",
    instructions=(
        "Filesystem MCP server for a resume-matching workflow. "
        "Use the exposed tools to inspect and process resume files."
    ),
)


def _safe_path(relative_path: str, root: Path = BASE_DIR) -> Path:
    """Resolve a path and prevent traversal outside the configured base."""
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Path escapes the configured filesystem root.")
    return candidate


def _file_info(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path.relative_to(BASE_DIR)),
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "extension": path.suffix.lower(),
    }


@mcp.resource("filesystem://config")
def filesystem_config() -> str:
    """Return server configuration as a JSON resource."""
    return json.dumps(
        {
            "base_dir": str(BASE_DIR),
            "resume_dir": str(RESUME_DIR),
            "output_dir": str(OUTPUT_DIR),
            "supported_resume_extensions": [".txt", ".md"],
            "server": "ResumeFileSystem",
        },
        indent=2,
    )


@mcp.resource("filesystem://resumes")
def resume_index() -> str:
    """Return the current resume index as a JSON resource."""
    items = [
        _file_info(p)
        for p in sorted(RESUME_DIR.iterdir())
        if p.is_file() and p.suffix.lower() in {".txt", ".md"}
    ]
    return json.dumps(items, indent=2)


@mcp.tool()
def list_files(directory: str = "resumes") -> list[dict[str, Any]]:
    """List files in a directory under the configured base directory."""
    path = _safe_path(directory)
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    if not path.is_dir():
        raise NotADirectoryError(directory)
    return [_file_info(p) for p in sorted(path.iterdir()) if p.is_file()]


@mcp.tool()
def read_file(path: str) -> str:
    """Read a UTF-8 text file under the configured base directory."""
    file_path = _safe_path(path)
    if not file_path.exists():
        raise FileNotFoundError(path)
    if not file_path.is_file():
        raise IsADirectoryError(path)
    return file_path.read_text(encoding="utf-8")


@mcp.tool()
def write_file(path: str, content: str) -> dict[str, Any]:
    """Create or replace a UTF-8 text file under the configured base directory."""
    file_path = _safe_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return {"status": "ok", "file": _file_info(file_path)}


@mcp.tool()
def delete_file(path: str) -> dict[str, str]:
    """Delete a file under the configured base directory."""
    file_path = _safe_path(path)
    if not file_path.exists():
        raise FileNotFoundError(path)
    if not file_path.is_file():
        raise IsADirectoryError(path)
    file_path.unlink()
    return {"status": "deleted", "path": path}


@mcp.tool()
def move_file(source: str, destination: str) -> dict[str, Any]:
    """Move a file inside the configured base directory."""
    src = _safe_path(source)
    dst = _safe_path(destination)
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(source)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return {"status": "moved", "file": _file_info(dst)}


@mcp.tool()
def watch_directory(
    directory: str = "resumes",
    duration_seconds: int = 15,
    poll_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    """
    Monitor a directory for newly created resume files.

    This portable implementation uses polling, so it works on Windows,
    macOS, and Linux without an additional filesystem watcher package.
    """
    if duration_seconds < 1 or duration_seconds > 300:
        raise ValueError("duration_seconds must be between 1 and 300.")
    directory_path = _safe_path(directory)
    if not directory_path.is_dir():
        raise NotADirectoryError(directory)

    before = {
        str(p.resolve())
        for p in directory_path.iterdir()
        if p.is_file()
    }
    deadline = time.time() + duration_seconds
    found: list[dict[str, Any]] = []

    while time.time() < deadline:
        awaitable_sleep = poll_seconds
        time.sleep(awaitable_sleep)
        current = {
            str(p.resolve())
            for p in directory_path.iterdir()
            if p.is_file()
        }
        new_files = current - before
        for raw in sorted(new_files):
            p = Path(raw)
            found.append(_file_info(p))
        if found:
            break

    return found


@mcp.tool()
def batch_process(
    directory: str = "resumes",
    pattern: str = "*.txt",
) -> dict[str, Any]:
    """
    Read multiple resume files efficiently and return structured records.

    The function is intentionally simple and deterministic so the LangGraph
    agent can perform the actual matching logic.
    """
    directory_path = _safe_path(directory)
    if not directory_path.is_dir():
        raise NotADirectoryError(directory)

    records = []
    for path in sorted(directory_path.glob(pattern)):
        if path.is_file():
            content = path.read_text(encoding="utf-8", errors="replace")
            records.append(
                {
                    "name": path.name,
                    "path": str(path.relative_to(BASE_DIR)),
                    "content": content,
                    "characters": len(content),
                }
            )

    return {"count": len(records), "files": records}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="MCP transport. stdio is used by the LangGraph client.",
    )
    args = parser.parse_args()

    if args.transport == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
