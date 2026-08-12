# Day 3 — Agent as a Network Service

## Raneem's Submission — Report Generation Agent

This project extends the Day 2 multi-agent architecture into a reusable
**Report Generation Agent** and exposes it through networked interfaces,
containers, MCP tools, and discoverable skills.

---

## 🚀 Overview

The Day 2 multi-agent workflow was extended so that users can provide a
report topic dynamically and receive a generated Markdown report as an
artifact.

### Multi-Agent Workflow

```text
User Topic
    │
    ▼
Supervisor
    │
    ├──► Researcher
    │
    ├──► Analyst
    │
    ├──► Writer
    │
    └──► Critic
             │
             ├── Revision ──► appropriate agent
             │
             └── Approved
                    │
                    ▼
              Final Report
                    │
                    ▼
             output/report.md
✨ What Was Implemented
1. Report Generation Agent

The report-generation workflow was implemented in:

src/report_agent.py

The user can provide a topic or research question dynamically.

Example:

Assess the challenges and recommendations for implementing federated
data governance in a healthcare organization.

The final approved report is saved automatically as:

output/report.md
2. FastAPI + OpenResponses

The agent was exposed as an HTTP service using FastAPI.

Endpoint	Purpose
GET /healthz	Service health check
POST /v1/responses	Submit a task to the agent
GET /.well-known/agent-card.json	Agent metadata

The /v1/responses endpoint implements a deliberate subset of the
OpenResponses response structure.

The agent is created once when the API starts rather than being rebuilt for
every request.

3. Docker

The agent API was containerized using Docker.

The Dockerfile separates dependency installation from source-code changes,
allowing Docker to reuse the dependency layer when only application code
changes.

A cache experiment demonstrated:

src/api.py changed
      ↓
Dependency layer reused

pyproject.toml changed
      ↓
Dependency layer rebuilt

The Docker image was successfully built and run.

4. Docker Compose

The application was converted from a single container into multiple services:

                 Docker Compose
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
    agent-api :8000           mcp :8001
       FastAPI                 FastMCP

The services communicate through the Compose network using the service name:

MCP_URL=http://mcp:8001/mcp

Both services were successfully started and verified with Docker Compose.

5. FastMCP Tools

An MCP server was implemented in:

src/mcp_server.py

It exposes two tools:

calculate
word_stats

The tools were successfully discovered and executed using a FastMCP client.

Example:

calculate("2*(3+4)**2")
→ 98.0

This demonstrates how tools can move from being local Python functions to
network-accessible capabilities through MCP.

6. Skills over MCP

The MCP server was extended with SkillsDirectoryProvider to expose skills as
MCP resources.

Available skills include:

skill://research-brief/SKILL.md
skill://data-governance-review/SKILL.md

The skills were successfully:

discovered
read
downloaded

The distinction between MCP tools and resources is:

MCP Tools
    ↓
Actions an agent can CALL

MCP Resources
    ↓
Knowledge an agent can RETRIEVE

The MCP server exposes the skill; the receiving agent is responsible for
interpreting and applying it.

7. Stateful vs. Stateless MCP

A FastMCP v4 client was used in an isolated environment to test both protocol
modes:

mode='auto'    → 2 tools
mode='legacy'  → 2 tools

Both modes successfully discovered the same MCP tools.

The experiment demonstrated that application state in a sessionless design
should be stored externally and addressed through an explicit state handle,
such as LangGraph's thread_id, rather than relying on connection-specific
session state.

This allows requests to be handled by different replicas and makes service
restarts easier to manage.

🏗️ Architecture
                         User
                          │
                          ▼
                ┌───────────────────┐
                │ Report Generation │
                │      Agent        │
                └─────────┬─────────┘
                          │
                          ▼
                    FastAPI :8000
                          │
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
        Agent Response          MCP Server :8001
                                      │
                              ┌───────┴───────┐
                              │               │
                              ▼               ▼
                           Tools           Skills
                              │               │
                    ┌─────────┴──────┐   ┌────┴─────────────┐
                    │                │   │                  │
               calculate        word_stats          research-brief
                                                    data-governance-review
📁 Project Structure
day3/
├── src/
│   ├── agent.py
│   ├── api.py
│   ├── mcp_server.py
│   └── report_agent.py
│
├── skills/
│   └── data-governance-review/
│       └── SKILL.md
│
├── output/
│   └── report.md
│
├── Dockerfile
├── compose.yaml
├── pyproject.toml
└── uv.lock