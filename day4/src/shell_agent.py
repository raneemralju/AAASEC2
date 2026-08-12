import os
from pathlib import Path

from dotenv import load_dotenv
from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from langchain_openai import ChatOpenAI

load_dotenv()

WORK_DIR = Path(__file__).resolve().parent.parent / "work"


def make_backend():
    backend = LocalShellBackend(
        root_dir=str(WORK_DIR),
        virtual_mode=True,
        env={"PATH": os.environ["PATH"]},
    )

    return backend, lambda: None


async def main():
    llm = ChatOpenAI(
        model="deepseek/deepseek-chat-v3-0324",
        api_key=os.environ["OPENAI_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
        max_tokens=2000,
    )

    backend, cleanup = make_backend()

    try:
        agent = create_deep_agent(
            model=llm,
            system_prompt=(
                "You are a coding agent. "
                "Use the filesystem and execute tools to complete the task."
            ),
            backend=backend,
        )

        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Create calculator.py with add, sub, mul, and div. "
                            "The div function must raise an error when dividing "
                            "by zero. Create pytest tests including the zero "
                            "division case. Run the tests using execute. "
                            "Fix any failures until all tests pass. "
                            "Finally, report the final pytest output."
                        ),
                    }
                ]
            }
        )

        print(result["messages"][-1].content)

    finally:
        cleanup()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())