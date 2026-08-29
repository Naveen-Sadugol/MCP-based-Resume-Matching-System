# 5–6 minute demo script

## Opening

"Today I am demonstrating an MCP-based resume matching system. The main change from the earlier architecture is that filesystem operations are no longer custom functions embedded in the agent. They are exposed through an independent MCP server."

## Server

"This FastMCP server exposes filesystem tools and resources. The server has list, read, write, delete and move operations, plus the assignment-specific watch_directory and batch_process capabilities."

## Resources

"The server exposes a configuration resource and a resume index resource. An MCP client can discover these resources rather than depending on hard-coded filesystem knowledge."

## Agent

"The LangGraph agent starts the MCP server over stdio, initializes a ClientSession, discovers tools/resources, calls batch_process, and then runs the matching graph."

## End-to-end

"Here I run the agent. It receives the job description, gets the resumes through MCP, scores them, and writes the final report through MCP."

## Tests

"Finally, I run pytest to verify path safety, batch processing, MCP-related filesystem behavior, and the matching algorithm."

## Closing

"The resulting architecture cleanly separates the AI workflow from external capabilities. This makes the filesystem service reusable by other MCP-compatible clients and keeps the agent focused on orchestration and matching."
