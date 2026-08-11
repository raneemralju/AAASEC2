"""
DAY 3 — Agent implementation.

READ FIRST:  ../01-deep-agents.md

Do not continue to api.py until:
    USE_FAKE=1 uv run python src/agent.py
prints a reply, AND (with real keys) the agent answers using its tools.

The contract this file must satisfy — the ONLY thing api.py will rely on:

    def build_agent() -> object with .ainvoke({"messages": [...]})

TODO:
  1. Two boring tools: calculate(expression) and current_time().
     (Boring is the point. Day 3 is about everything AROUND the agent.)
  2. build_agent():
       - if USE_FAKE: return a FakeAgent with the same .ainvoke shape
       - else: create_deep_agent(model=<ChatOpenAI via OpenRouter>,
                                 tools=[...], system_prompt=...,
                                 backend=FilesystemBackend(root_dir=<day3/>,
                                                           virtual_mode=True),
                                 skills=["/skills/"])
  3. A __main__ smoke test that invokes the agent once and prints the reply.

NOTE: default backends give the agent FILESYSTEM tools but NO shell.
An execute tool requires a sandbox backend — that is Day 4, on purpose.
"""

# TODO

import ast
import operator
from datetime import datetime

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
load_dotenv()


_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def calculate(expression: str):
    """Safely evaluate a basic arithmetic expression."""

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
            left = evaluate(node.left)
            right = evaluate(node.right)
            return _ALLOWED_OPERATORS[type(node.op)](left, right)

        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
            operand = evaluate(node.operand)
            return _ALLOWED_OPERATORS[type(node.op)](operand)

        raise ValueError("Unsupported expression")

    tree = ast.parse(expression, mode="eval")
    return evaluate(tree)


def current_time():
    """Return the current local date and time."""
    return datetime.now().astimezone().isoformat()

class FakeAgent:
    async def ainvoke(self, input_data):
        return {
            "messages": [
                AIMessage(
                    content="Fake agent reply — the agent pipeline is working."
                )
            ]
        }

def build_agent():
    if os.getenv("USE_FAKE") == "1":
        return FakeAgent()

    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model="deepseek/deepseek-chat-v3-0324",
        api_key=os.environ["OPENAI_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
        max_tokens=2000,
    )
    project_root = Path(__file__).resolve().parent.parent

    return create_deep_agent(
        model=llm,
        tools=[calculate, current_time],
        system_prompt=(
            "You are a helpful assistant. "
            "Always use the calculate tool for arithmetic. "
            "Always use the current_time tool when asked for the current time."
        ),
        backend=FilesystemBackend(
            root_dir=project_root,
            virtual_mode=True,
        ),
        skills=["/skills/"],
    )

if __name__ == "__main__":
    import asyncio

    async def main():
        agent = build_agent()

        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content":"Review this data governance scenario: An organization allows employees from different departments to access customer data, but there is no documented data owner or access policy. Provide a data governance review.",
                    }
                ]
            }
        )

        print(result["messages"][-1].content)

    asyncio.run(main())