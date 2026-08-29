"""
LangGraph resume matching agent using the filesystem MCP server.

The agent does NOT import or call the filesystem implementation directly.
It starts an MCP subprocess and discovers/calls MCP tools through the client.

Run:
    python matching_agent.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER_FILE = Path(__file__).resolve().with_name(
    "filesystem_mcp_server.py"
)


class AgentState(TypedDict, total=False):
    job_description: str
    resumes: list[dict[str, Any]]
    matches: list[dict[str, Any]]
    report: str


def extract_keywords(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{1,}", text.lower())
    stop_words = {
        "and", "the", "with", "for", "from", "that", "this", "are",
        "you", "will", "have", "has", "our", "your", "into", "using",
        "years", "year", "experience", "work", "role", "job", "team",
    }
    return {w for w in words if w not in stop_words and len(w) > 2}


def score_resume(job_description: str, resume_text: str) -> tuple[float, list[str]]:
    job_words = extract_keywords(job_description)
    resume_words = extract_keywords(resume_text)
    if not job_words:
        return 0.0, []

    matched = sorted(job_words & resume_words)
    score = round((len(matched) / len(job_words)) * 100, 2)
    return score, matched


async def call_mcp_tool(session: ClientSession, name: str, arguments: dict[str, Any]) -> Any:
    result = await session.call_tool(name, arguments)
    if result.isError:
        raise RuntimeError(f"MCP tool '{name}' returned an error.")
    if result.structuredContent:
        return result.structuredContent
    if result.content:
        first = result.content[0]
        if hasattr(first, "text"):
            try:
                return json.loads(first.text)
            except json.JSONDecodeError:
                return first.text
    return None


async def discover_mcp(session: ClientSession) -> dict[str, Any]:
    """Demonstrate resource/tool discovery through MCP."""
    tools = await session.list_tools()
    resources = await session.list_resources()
    return {
        "tools": [tool.name for tool in tools.tools],
        "resources": [str(resource.uri) for resource in resources.resources],
    }


async def run_agent(job_description: str) -> dict[str, Any]:
    server_params = StdioServerParameters(
    command=sys.executable,
    args=[str(SERVER_FILE)],
)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            discovery = await discover_mcp(session)

            batch = await call_mcp_tool(
                session,
                "batch_process",
                {"directory": "resumes", "pattern": "*.txt"},
            )

            state: AgentState = {
                "job_description": job_description,
                "resumes": batch["files"],
                "matches": [],
            }

            graph = build_graph(session)
            final_state = await graph.ainvoke(state)
            final_state["mcp_discovery"] = discovery
            return final_state


def build_graph(session: ClientSession):
    workflow = StateGraph(AgentState)

    async def match_resumes(state: AgentState) -> AgentState:
        matches = []
        for resume in state.get("resumes", []):
            score, keywords = score_resume(
                state["job_description"],
                resume["content"],
            )
            matches.append(
                {
                    "name": resume["name"],
                    "path": resume["path"],
                    "score": score,
                    "matched_keywords": keywords,
                }
            )
        matches.sort(key=lambda x: x["score"], reverse=True)
        return {"matches": matches}

    async def create_report(state: AgentState) -> AgentState:
        lines = [
            "# Resume Matching Report",
            "",
            "## Job Description",
            state["job_description"],
            "",
            "## Ranked Candidates",
        ]
        for index, item in enumerate(state["matches"], start=1):
            lines.append(
                f"{index}. **{item['name']}** — {item['score']}% "
                f"keyword match — {', '.join(item['matched_keywords']) or 'none'}"
            )

        report = "\n".join(lines)

        # Writing the report is also performed through MCP, not direct I/O.
        await call_mcp_tool(
            session,
            "write_file",
            {"path": "output/matching_report.md", "content": report},
        )
        return {"report": report}

    workflow.add_node("match_resumes", match_resumes)
    workflow.add_node("create_report", create_report)
    workflow.add_edge(START, "match_resumes")
    workflow.add_edge("match_resumes", "create_report")
    workflow.add_edge("create_report", END)

    return workflow.compile()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--job",
        default=(
            "Python developer with SQL, Git, Docker, Linux, REST APIs, "
            "problem solving and backend development experience."
        ),
        help="Job description used for matching.",
    )
    args = parser.parse_args()

    result = await run_agent(args.job)

    print("\n=== MCP DISCOVERY ===")
    print("Tools:")
    for name in result["mcp_discovery"]["tools"]:
        print(f"  - {name}")
    print("Resources:")
    for uri in result["mcp_discovery"]["resources"]:
        print(f"  - {uri}")

    print("\n=== MATCHING RESULTS ===")
    for item in result["matches"]:
        print(
            f"{item['name']}: {item['score']}% | "
            f"{', '.join(item['matched_keywords']) or 'no matched keywords'}"
        )

    print("\nReport saved through MCP: data/output/matching_report.md")


if __name__ == "__main__":
    asyncio.run(main())
