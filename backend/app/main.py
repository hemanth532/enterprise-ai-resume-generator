import asyncio
import io
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from .utils.docx_parser import parse_resume_bytes
from .utils.observability import write_step_observability
from .utils.resume_writer import resume_to_docx_bytes
from .orchestrator import run_pipeline
from .agents.llm_client import LLMClient
import uvicorn

app = FastAPI(title="AI Resume Enterprise - Backend")
app.state.progress_queues = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    llm_client = LLMClient()
    if not llm_client.ping():
        raise RuntimeError(
            f"LLM service is unreachable at {llm_client.ollama_server if llm_client.use_ollama else llm_client.base_url}. "
            "Make sure Ollama is running and the model is available."
        )
    app.state.llm_client = llm_client


@app.get("/health")
def health():
    llm_client = getattr(app.state, "llm_client", None)
    llm_status = None
    if llm_client is not None:
        llm_status = {
            "model": llm_client.model,
            "use_ollama": llm_client.use_ollama,
            "server": llm_client.ollama_server if llm_client.use_ollama else llm_client.base_url,
            "reachable": llm_client.ping(),
        }
    return {"status": "ok", "llm": llm_status}


async def send_progress(session_id: str, step: str, status: str, detail: str) -> None:
    queue = app.state.progress_queues.get(session_id)
    if queue is None:
        return
    await queue.put({"step": step, "status": status, "detail": detail})


@app.websocket("/ws/progress/{session_id}")
async def progress_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue()
    app.state.progress_queues[session_id] = queue
    try:
        await websocket.send_json({"step": "connection", "status": "connected", "detail": "Progress stream active"})
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        app.state.progress_queues.pop(session_id, None)


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    allowed = (".doc", ".docx", ".pdf")
    file_name = file.filename or "resume"
    suffix = Path(file_name).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail="Only .doc, .docx, and .pdf files are supported")
    content = await file.read()
    try:
        parsed = parse_resume_bytes(content, file_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse(content={"filename": file.filename, "parsed": parsed})






@app.post("/pipeline/resume-docx")
async def pipeline_resume_docx(payload: dict):
    pipeline = payload.get("pipeline")
    if not pipeline:
        raise HTTPException(status_code=400, detail="Missing 'pipeline' in payload")

    try:
        docx_bytes = resume_to_docx_bytes(pipeline)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=enhanced_resume.docx"},
    )

@app.post("/pipeline/run")
async def pipeline_run(payload: dict):
    """Run the full orchestrated pipeline. Accepts either `parsed` (from /upload-resume) or raw `text`.
    Example payload: {"parsed": {"paragraphs": [...]}}"""
    parsed = payload.get("parsed")
    session_id = payload.get("session_id")
    if not parsed:
        raise HTTPException(status_code=400, detail="Missing 'parsed' in payload")

    async def progress_callback(step: str, status: str, detail: str) -> None:
        if not session_id:
            return
        await asyncio.gather(
            send_progress(session_id, step, status, detail),
            write_step_observability(session_id, step, status, detail),
        )

    try:
        result = await run_pipeline(parsed, progress_callback if session_id else None)
    except Exception as exc:
        error_detail = str(exc)
        if session_id:
            await send_progress(session_id, "pipeline", "failed", error_detail)
        raise HTTPException(status_code=502, detail=error_detail)
    return JSONResponse(content={"pipeline": result})


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
