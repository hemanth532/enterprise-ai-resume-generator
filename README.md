# Enterprise AI Resume Generator Agent

A full-stack enterprise resume generation project with a React + TypeScript frontend and a FastAPI backend.

## Project Structure

- `frontend/` — React application for file upload, live WebSocket progress, result viewing, and downloads
- `backend/` — FastAPI service for resume parsing, LLM pipeline orchestration, observability logging, and enhanced `.docx` resume export

## Features

- Upload `.doc`, `.docx`, and `.pdf` resumes
- Parse resume content and run a structured LLM-powered pipeline
- Stream progress updates through WebSockets
- Show pipeline results in expandable/collapsible sections
- Download both parsed JSON and enhanced `.docx` resumes
- Configurable LLM backend using local Ollama or remote API providers

## Prerequisites

- Node.js 18+ and npm
- Python 3.11+ and pip
- Recommended: system-level `pandoc` for `.doc` conversion support
- Optional: local Ollama running at `http://localhost:11434`

## Backend Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # PowerShell on Windows
# or .\.venv\Scripts\activate  # cmd.exe on Windows
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file or export variables before running:

- `USE_OLLAMA=true` — use local Ollama by default
- `OLLAMA_SERVER=http://localhost:11434`
- `QWEN_MODEL=qwen2:latest`
- `OLLAMA_TIMEOUT=600`
- `QWEN_API_KEY` or `OPENAI_API_KEY` — required when not using Ollama

### Run Backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Setup

```bash
cd frontend
npm install
```

### Run Frontend

```bash
cd frontend
npm run dev
```

Open the displayed local URL in your browser, typically `http://localhost:5173`.

## API Endpoints

The frontend communicates with the backend via:

- `GET /health` — health and LLM connectivity status
- `POST /upload-resume` — upload `.doc`, `.docx`, or `.pdf` resume files
- `POST /pipeline/run` — run the analysis pipeline on parsed resume data
- `POST /pipeline/resume-docx` — generate enhanced `.docx` resume output
- `WS /ws/progress/{session_id}` — receive live progress updates

## Notes

- The current frontend assumes the backend is available at `http://localhost:8000`.
- `.doc` file support relies on `pypandoc` plus a system-installed `pandoc` binary.
- `.pdf` parsing is handled by `PyPDF2`.
- If using local Ollama, ensure the model is installed and available.

## Cleanup

This repository uses a single root-level README. Subfolder READMEs are not required and have been removed.
