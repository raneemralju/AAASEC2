# ============================================================
# DAY 2 LAB — SKELETON: Build a Multi-Agent Research Team
# ============================================================
# Fill in every TODO. Don't open the solution (day2_lab_solution.py)
# until you pass the self-check at the bottom.
#
# WHAT CHANGES FROM DAY 1 — read this table twice:
#
#   Day 1 (single agent)              Day 2 (multi-agent)
#   ─────────────────────             ─────────────────────────────
#   nodes = Python functions          nodes = LLM agents w/ personas
#   routing = your if/else            routing = supervisor LLM decides
#   one prompt for everything         one system prompt PER agent
#   tools available everywhere        tools SCOPED (only researcher
#                                       can search the web)
#   loop = quality-score retry        loop = critic sends draft back
#                                       to writer for revision
#
# What does NOT change: State + Nodes + Edges. A multi-agent system
# is STILL just a StateGraph. If you can build Day 1, you can build
# this — the new ideas are personas, the supervisor, and guardrails.
#
# The system you're building (the SUPERVISOR pattern):
#
#              ┌──────────── supervisor ─────────────┐
#              │       (LLM decides who's next)      │
#     ┌────────┼───────────┬───────────┬─────────────┤
#     ↓        ↓           ↓           ↓             ↓
#  researcher  analyst    writer     critic       FINISH
#     │        │           │           │             ↓
#     └────────┴───────────┴───────────┘            END
#          (every worker reports back to the supervisor)
#
# Recommended reading BEFORE you start (~25 min):
#   1. Multi-agent concepts (architectures, supervisor pattern):
#      https://docs.langchain.com/oss/python/langgraph/multi-agent
#   2. Refresh: conditional branching + loops (you need both again):
#      https://docs.langchain.com/oss/python/langgraph/use-graph-api#conditional-branching
#   3. Structured output (the supervisor's decision is structured!):
#      https://docs.langchain.com/oss/python/langchain/structured-output
#
# Setup: same as Day 1 — `uv sync`, keys in .env, or USE_FAKE=1.
# ============================================================

import os
import operator
from datetime import datetime
from typing import Annotated, List, Literal
from typing_extensions import TypedDict

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, SystemMessage

from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from pathlib import Path



# TODO STEP 0 — same imports as Day 1:
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver


load_dotenv()

MAX_REVISIONS = 2      # cap on writer↔critic loops
MAX_TURNS = 12         # cap on total supervisor decisions



class TeamState(TypedDict):
    task: str
    research_notes: Annotated[List[str], operator.add]
    analysis: str
    draft: str
    critique: str
    revision_count: int
    turn_count: int
    next_agent: str
    execution_logs: Annotated[List[str], operator.add]


# ============================================================
# STEP 2 — STRUCTURED ROUTING DECISION
# ============================================================

class RouterDecision(BaseModel):
    """The supervisor's choice of who acts next."""
    next_agent: Literal["researcher", "analyst", "writer", "critic", "FINISH"]
    reason: str = Field(description="One sentence explaining the choice")


# ============================================================
# STEP 3 — ONE LLM, FOUR PERSONAS (+ tools scoped per agent)
# ============================================================

PERSONAS = {
    "researcher": """
You are the Researcher on a multi-agent research team.

Your job is to find and summarize relevant evidence from the provided web search results.
Focus on factual information, useful sources, and key evidence related to the task.

You MUST NOT analyze the evidence, write the final report, or critique another agent's work.
Return concise research notes that the analyst can use.
""",

    "analyst": """
You are the Analyst on a multi-agent research team.

Your job is to analyze the research notes and identify the main findings,
patterns, benefits, risks, trade-offs, and implications relevant to the task.

You MUST NOT perform web searches, write the final report, or critique the draft.
Base your analysis only on the research available in the shared state.
""",

    "writer": """
You are the Writer on a multi-agent research team.

Your job is to turn the available research and analysis into a clear,
well-structured report draft that directly answers the task.

You MUST NOT perform web searches or evaluate the quality of the draft.
When a critique is provided, revise the existing draft according to the critique.
""",

    "critic": """
You are the Critic on a multi-agent research team.

Your job is to review the current draft against the research and analysis.
Check factual support, completeness, clarity, and whether the draft answers the task.

You MUST NOT rewrite the draft, perform web searches, or produce the final report.

Reply with exactly one of:
APPROVED
or
REVISE: <specific fixes needed>
"""
}

llm = ChatOpenAI(
    model="nvidia/nemotron-3-super-120b-a12b:free",
    temperature=0,
    base_url="https://openrouter.ai/api/v1",
)

search_tool = TavilySearch(max_results=4)

supervisor_llm = llm.with_structured_output(RouterDecision)

def run_persona(role, user_content):
    response = llm.invoke([
        SystemMessage(content=PERSONAS[role]),
        HumanMessage(content=user_content),
    ])
    return response.content

# ============================================================
# STEP 4 — THE SUPERVISOR NODE (the piece Day 1 didn't have)
# ============================================================


def supervisor_node(state: TeamState):
    # 1. Increment turn count
    turn_count = state["turn_count"] + 1

    # 2. Build a compact status summary
    status = f"""
Task: {state["task"]}

Research notes available: {len(state["research_notes"])}
Analysis available: {bool(state["analysis"])}
Draft available: {bool(state["draft"])}
Critique: {state["critique"][:500] if state["critique"] else "None"}
Revision count: {state["revision_count"]}
Turn count: {turn_count}
"""

    # 3. Ask the supervisor LLM for the next agent
    decision = supervisor_llm.invoke([
        SystemMessage(
            content="""
You are the supervisor of a multi-agent research team.

Decide which agent should act next based on the current status.

Use this general workflow:
- researcher: gather research when research is missing
- analyst: analyze research when analysis is missing
- writer: create or revise the draft
- critic: review an existing draft
- FINISH: when the draft is approved or the work is otherwise complete

Return the best next step based on the current state.
"""
        ),
        HumanMessage(content=status),
    ])

    next_agent = decision.next_agent

    # 4a. Guardrail: maximum number of turns
    if turn_count > MAX_TURNS:
        next_agent = "FINISH"

    # 4b. Guardrail: maximum number of revisions
    elif (
        next_agent in {"writer", "critic"}
        and state["revision_count"] >= MAX_REVISIONS
        and state["draft"]
    ):
        next_agent = "FINISH"

    # 5. Return only the fields this node updates
    return {
        "next_agent": next_agent,
        "turn_count": turn_count,
        "execution_logs": [
            f"Supervisor selected {next_agent} "
            f"(reason: {decision.reason})"
        ],
    }


# ============================================================
# STEP 5 — WORKER AGENT NODES
# ============================================================
# Each worker: read the blackboard → act in persona → return a
# PARTIAL update with ONLY its own section (Day 1 rule, unchanged).

def researcher_node(state: TeamState):
    """Search the web (ONLY this agent may), condense to notes."""

    results = search_tool.invoke({
        "query": state["task"]
    })["results"]

    raw = "\n\n".join(
        f"Title: {r.get('title', '')}\n"
        f"Content: {r.get('content', '')}\n"
        f"URL: {r.get('url', '')}"
        for r in results
    )

    notes = run_persona(
        "researcher",
        f"""
Task: {state["task"]}

Search results:

{raw}

Condense these results into useful research notes.
"""
    )

    return {
        "research_notes": [notes],
        "execution_logs": [
            f"Researcher collected {len(results)} search results"
        ],
    }


def analyst_node(state: TeamState):
    """Turn raw notes into analysis."""

    notes = "\n\n".join(state["research_notes"])

    analysis = run_persona(
        "analyst",
        f"""
Task: {state["task"]}

Research notes:

{notes}

Analyze the research and identify the most important findings,
patterns, benefits, risks, trade-offs, and implications.
"""
    )

    return {
        "analysis": analysis,
        "execution_logs": [
            "Analyst completed the research analysis"
        ],
    }

def writer_node(state: TeamState):
    """Write the draft — or REVISE it if a critique is present."""

    revising = (
        bool(state["critique"])
        and state["critique"].startswith("REVISE")
    )

    if revising:
        prompt = f"""
Task: {state["task"]}

Research notes:
{chr(10).join(state["research_notes"])}

Analysis:
{state["analysis"]}

Previous draft:
{state["draft"]}

Critique:
{state["critique"]}

Revise the previous draft according to the critique.
Keep the useful content, fix the identified problems, and produce
a complete improved draft.
"""
    else:
        prompt = f"""
Task: {state["task"]}

Research notes:
{chr(10).join(state["research_notes"])}

Analysis:
{state["analysis"]}

Write a clear, well-structured research report draft that answers
the task and is supported by the available research.
"""

    draft = run_persona("writer", prompt)

    return {
        "draft": draft,
        "critique": "",
        "revision_count": (
            state["revision_count"] + 1 if revising
            else state["revision_count"]
        ),
        "execution_logs": [
            "Writer revised the draft" if revising
            else "Writer created the initial draft"
        ],
    }


def critic_node(state: TeamState):
    """Review the draft against the research notes."""

    notes = "\n\n".join(state["research_notes"])

    critique = run_persona(
        "critic",
        f"""
Task: {state["task"]}

Research notes:
{notes}

Analysis:
{state["analysis"]}

Current draft:
{state["draft"]}

Review the draft against the research and analysis.

Respond with exactly one of:

APPROVED

or

REVISE: <specific fixes needed>
"""
    )

    return {
        "critique": critique,
        "execution_logs": [
            f"Critic decision: {critique}"
        ],
    }


# ============================================================
# STEP 6 — ROUTING FUNCTION + WIRE THE GRAPH
# ============================================================

# TODO: route_from_supervisor + graph wiring
def route_from_supervisor(state: TeamState) -> str:
    return state["next_agent"]


workflow = StateGraph(TeamState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("writer", writer_node)
workflow.add_node("critic", critic_node)

workflow.add_edge(START, "supervisor")


workflow.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "researcher": "researcher",
        "analyst": "analyst",
        "writer": "writer",
        "critic": "critic",
        "FINISH": END,
    },
)

for worker in ["researcher", "analyst", "writer", "critic"]:
    workflow.add_edge(worker, "supervisor")


# ============================================================
# STEP 7 — COMPILE, VISUALIZE, RUN
# ============================================================
app = workflow.compile(checkpointer=InMemorySaver())

def save_report(report: str, topic: str) -> Path:
    """Save the final approved report as a Markdown artifact."""
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    report_path = output_dir / "report.md"

    content = f"""# Generated Report

**Topic:** {topic}

---

{report}
"""

    report_path.write_text(content, encoding="utf-8")

    return report_path

if __name__ == "__main__":
    task = input("\nEnter the report topic or question: ").strip()

    if not task:
        task = "Assess the benefits and challenges of adopting multi-agent AI systems in 2026."

    initial_state = {
        "task": task,
        "research_notes": [],
        "analysis": "",
        "draft": "",
        "critique": "",
        "revision_count": 0,
        "turn_count": 0,
        "next_agent": "",
        "execution_logs": [],
    }

    print(app.get_graph().draw_mermaid())

    config = {
        "configurable": {
            "thread_id": "day2-run-1"
        }
    }

    final_state = None

    for state in app.stream(
        initial_state,
        config,
        stream_mode="values",
    ):
        final_state = state

    print("\n" + "=" * 60)
    print("FINAL DRAFT")
    print("=" * 60)
    print(final_state["draft"])

    report_path = save_report(final_state["draft"], task)
    print("\n" + "=" * 60)
    print("REPORT SAVED")
    print("=" * 60)
    print(report_path)

    print("\n" + "=" * 60)
    print("EXECUTION LOGS")
    print("=" * 60)

    for log in final_state["execution_logs"]:
        print("-", log)

    print(f"\nTurns: {final_state['turn_count']}")
    print(f"Revisions: {final_state['revision_count']}")


# ============================================================
# SELF-CHECK before you look at the solution
# ============================================================
# [ ] I can explain the supervisor pattern in one sentence
# [ ] My routing function reads state — the DECISION was made in a node
# [ ] research_notes appends; draft overwrites; I know why each
# [ ] The writer RESETS critique — I can explain what breaks if not
#     (hint: what does the supervisor see on the turn after a revision?)
# [ ] Only researcher_node touches search_tool
# [ ] My supervisor has BOTH guardrails, and I triggered EXPERIMENT 2
# [ ] My Mermaid diagram is a star: supervisor in the middle
# [ ] I can name one task where Day 1's single agent is the BETTER
#     design (multi-agent is not free: more calls, more latency,
#     more places to break — coordination must earn its cost)
#
# Stuck? Debugging order that works:
#   1. stream_mode="updates" — watch each supervisor decision + reason
#   2. print the status summary your supervisor_node builds — is the
#      LLM seeing an accurate picture of the blackboard?
#   3. check your conditional-edge dict covers ALL five decisions
#   4. only THEN open day2_lab_solution.py
# ============================================================
