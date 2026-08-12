"""
DAY 3 — HTTP API.

FastAPI exposes the agent as an HTTP service using a small
OpenResponses-compatible response shape.
"""

import os
import time
import uuid

from fastapi import FastAPI
from pydantic import BaseModel

from .agent import build_agent


app = FastAPI(title="Day 3 Agent API")

# Build the agent once when the API starts.
agent = build_agent()


class ResponseRequest(BaseModel):
    input: str
    model: str | None = None


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/v1/responses")
async def create_response(request: ResponseRequest):
    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": request.input,
                }
            ]
        }
    )

    message = result["messages"][-1]
    text = message.content

    return {
        "id": f"resp_{uuid.uuid4().hex}",
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "model": request.model or "day3-agent",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": text,
                    }
                ],
            }
        ],
    }


@app.get("/.well-known/agent-card.json")
async def agent_card():
    student_name = os.getenv("STUDENT_NAME", "student")
    public_url = os.getenv("PUBLIC_URL", "http://localhost:8000")
    
    return {
        "name": student_name,
        "url": f"{public_url}/v1/responses",
        "todo": True,
    }
