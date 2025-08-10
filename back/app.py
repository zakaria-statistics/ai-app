from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import AsyncIterator
from queue import Queue, Empty
import asyncio, time, threading

from agent import get_agent, get_stream_chain

app = FastAPI(title="AI App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# singletons
agent = get_agent()
stream_chain = get_stream_chain()

@app.get("/health")
def health():
    return {"ok": True}

class Prompt(BaseModel):
    prompt: str

def _normalize_agent_result(res) -> str:
    """Always return a readable string from AgentExecutor result."""
    if isinstance(res, dict):
        if "output" in res and isinstance(res["output"], str):
            return res["output"]
        if "text" in res and isinstance(res["text"], str):
            return res["text"]
        return str(res)
    return str(res)

@app.post("/ask")
def ask_user(body: Prompt):
    try:
        res = agent.invoke(body.prompt)
        return {"response": _normalize_agent_result(res)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

class Question(BaseModel):
    question: str

async def _sse_from_chain(question: str) -> AsyncIterator[bytes]:
    """
    Streams SSE frames: 'data: <chunk>\\n\\n' + heartbeats.
    Bridges LangChain's sync .stream() using a background thread.
    """
    q: Queue = Queue(maxsize=100)

    def worker():
        try:
            for piece in stream_chain.stream({"input": question}):
                q.put(piece)
        except Exception as e:
            q.put(e)
        finally:
            q.put(None)  # sentinel

    threading.Thread(target=worker, daemon=True).start()

    last = time.time()
    heartbeat_every = 1.0

    while True:
        # heartbeat to keep the connection alive
        now = time.time()
        if now - last >= heartbeat_every:
            yield b": heartbeat\n\n"
            last = now

        try:
            item = q.get(timeout=0.1)
        except Empty:
            await asyncio.sleep(0.05)
            continue

        if item is None:
            yield b"data: [DONE]\n\n"
            break
        if isinstance(item, Exception):
            msg = str(item).replace("\n", " ")
            yield f"data: [STREAM ERROR] {msg}\n\n".encode("utf-8")
            break

        text = str(item).replace("\r", "")
        yield f"data: {text}\n\n".encode("utf-8")
        last = time.time()

@app.post("/ask_sse_post")
async def ask_sse_post(body: Question):
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="Empty question.")
    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
    return StreamingResponse(
        _sse_from_chain(body.question.strip()),
        media_type="text/event-stream",
        headers=headers,
    )
