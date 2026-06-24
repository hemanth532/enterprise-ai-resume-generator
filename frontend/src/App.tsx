import React, { useEffect, useMemo, useRef, useState } from 'react'

const API_BASE = ((import.meta as any).env?.VITE_BACKEND_URL as string) || 'http://localhost:8000'

const stepDefinitions = [
  { key: 'profile_analysis', label: 'Profile analysis' },
  { key: 'ats_optimization', label: 'ATS optimization' },
  { key: 'resume_generation', label: 'Resume generation' },
  { key: 'resume_review', label: 'Resume review' },
]

const initialProgressSteps = stepDefinitions.reduce<Record<string, { status: string; detail: string }>>(
  (acc, step) => {
    acc[step.key] = { status: 'pending', detail: '' }
    return acc
  },
  {}
)

export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [parsed, setParsed] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)
  const [pipelineResult, setPipelineResult] = useState<any | null>(null)
  const [health, setHealth] = useState<any | null>(null)
  const [wsStatus, setWsStatus] = useState('disconnected')
  const [progressSteps, setProgressSteps] = useState(initialProgressSteps)
  const [progressEvents, setProgressEvents] = useState<any[]>([])
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({})
  const [sessionId] = useState(() => crypto.randomUUID?.() ?? `session-${Date.now()}`)
  const socketRef = useRef<WebSocket | null>(null)

  const completedCount = useMemo(
    () => stepDefinitions.filter((step) => progressSteps[step.key].status === 'completed').length,
    [progressSteps],
  )
  const progressPercent = useMemo(() => Math.round((completedCount / stepDefinitions.length) * 100), [completedCount])

  useEffect(() => {
    async function fetchHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`)
        if (!res.ok) throw new Error('Health check failed')
        setHealth(await res.json())
      } catch (error) {
        setHealth({ status: 'unreachable', llm: null })
      }
    }

    fetchHealth()
  }, [])

  useEffect(() => {
    const apiUrl = new URL(API_BASE)
    const protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${apiUrl.host}/ws/progress/${sessionId}`
    const socket = new WebSocket(wsUrl)
    socketRef.current = socket

    socket.onopen = () => {
      setWsStatus('connected')
    }

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.step === 'connection') return

        setProgressSteps((prev) => ({
          ...prev,
          [data.step]: { status: data.status, detail: data.detail },
        }))
        setProgressEvents((prev) => [...prev, data])
      } catch (error) {
        console.error('Invalid progress message', error)
      }
    }

    socket.onclose = () => {
      setWsStatus('disconnected')
    }

    socket.onerror = () => {
      setWsStatus('error')
    }

    return () => {
      socket.close()
    }
  }, [sessionId])

  async function upload() {
    if (!file) return
    setLoading(true)
    setPipelineResult(null)
    setProgressSteps(initialProgressSteps)
    setProgressEvents([])

    const fd = new FormData()
    fd.append('file', file)

    try {
      const res = await fetch(`${API_BASE}/upload-resume`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error('Upload failed')
      const data = await res.json()
      setParsed(data.parsed)
    } catch (e) {
      console.error(e)
      alert('Upload failed')
    } finally {
      setLoading(false)
    }
  }

  async function runPipeline() {
    if (!parsed) return alert('Upload a resume file first')
    setLoading(true)
    setPipelineResult(null)
    setProgressSteps(initialProgressSteps)
    setProgressEvents([])

    try {
      const res = await fetch(`${API_BASE}/pipeline/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parsed, session_id: sessionId }),
      })
      if (!res.ok) throw new Error('Pipeline failed')
      const data = await res.json()
      setPipelineResult(data.pipeline)
    } catch (e) {
      console.error(e)
      alert('Pipeline call failed')
    } finally {
      setLoading(false)
    }
  }

  async function downloadEnhancedResume() {
    if (!pipelineResult) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/pipeline/resume-docx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pipeline: pipelineResult }),
      })
      if (!res.ok) throw new Error('Resume download failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'enhanced_resume.docx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error(error)
      alert('Download enhanced resume failed')
    } finally {
      setLoading(false)
    }
  }

  function toggleSection(section: string) {
    setOpenSections((prev) => ({ ...prev, [section]: !prev[section] }))
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
      <div className="max-w-4xl w-full rounded-3xl border border-slate-700 bg-slate-900/90 p-8 shadow-2xl shadow-slate-950/30">
        <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-semibold">Enterprise AI Resume Generator Agent</h1>
            <p className="text-slate-400 mt-2">Upload a resume file and generate an enhanced professional document.</p>
          </div>
          <div className="rounded-2xl border border-slate-700 bg-slate-950/80 px-4 py-3 text-sm text-slate-300">
            <p className="font-medium">Backend status</p>
            <p>status: {health?.status ?? 'loading...'}</p>
            <p>LLM: {health?.llm?.model ?? 'unknown'}</p>
            <p>WS: {wsStatus}</p>
          </div>
        </header>

        <section className="mb-6 rounded-3xl border border-slate-700 bg-slate-800/80 p-5">
          <h2 className="text-xl font-semibold mb-3">Resume Upload</h2>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <input
              type="file"
              accept=".doc,.docx,.pdf"
              onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
              className="block w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 file:border-0 file:bg-slate-700 file:px-4 file:py-2 file:text-slate-100"
            />
            <button
              onClick={upload}
              disabled={!file || loading}
              className="rounded-full bg-sky-500 px-5 py-2 text-white transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Upload Resume
            </button>
          </div>
        </section>

        {parsed && (
          <section className="mb-6 rounded-3xl border border-slate-700 bg-slate-800/80 p-5">
            <div className="flex items-center justify-between gap-3 mb-3">
              <h2 className="text-xl font-semibold">Parsed Resume Content</h2>
              <button
                onClick={() => setParsed(null)}
                className="rounded-full border border-slate-600 px-3 py-1 text-sm text-slate-200 hover:bg-slate-700"
              >
                Clear
              </button>
            </div>
            {parsed.paragraphs?.length ? (
              <div className="space-y-3 text-slate-300 text-sm max-h-64 overflow-auto">
                {parsed.paragraphs.map((paragraph: string, index: number) => (
                  <p key={index} className="rounded-xl bg-slate-950/50 p-3">
                    {paragraph}
                  </p>
                ))}
              </div>
            ) : (
              <pre className="text-slate-300 text-sm">{JSON.stringify(parsed, null, 2)}</pre>
            )}
          </section>
        )}

        <section className="mb-6 rounded-3xl border border-slate-700 bg-slate-800/80 p-5">
          <h2 className="text-xl font-semibold mb-3">Pipeline</h2>
          <p className="text-slate-400 mb-4">Run the backend pipeline after parsing the resume.</p>
          <button
            onClick={runPipeline}
            disabled={!parsed || loading}
            className="rounded-full bg-indigo-500 px-5 py-2 text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Run Pipeline
          </button>
        </section>

        <section className="mb-6 rounded-3xl border border-slate-700 bg-slate-800/80 p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">Progress</h2>
              <p className="text-slate-400 text-sm">Real-time step progress over WebSocket.</p>
            </div>
            <div className="rounded-full border border-slate-700 bg-slate-950/80 px-3 py-1 text-xs uppercase tracking-wide text-slate-300">
              {wsStatus}
            </div>
          </div>

          <div className="mb-4 h-3 overflow-hidden rounded-full bg-slate-900">
            <div style={{ width: `${progressPercent}%` }} className="h-full rounded-full bg-gradient-to-r from-sky-500 to-emerald-500 transition-all duration-500" />
          </div>
          <p className="text-right text-xs text-slate-400">{progressPercent}% complete</p>

          <div className="space-y-3 mt-4">
            {stepDefinitions.map((step) => {
              const info = progressSteps[step.key]
              const statusClass =
                info.status === 'completed'
                  ? 'bg-emerald-500 text-emerald-900'
                  : info.status === 'running'
                  ? 'bg-sky-500 text-slate-950'
                  : 'bg-slate-700 text-slate-100'

              return (
                <div key={step.key} className="rounded-2xl border border-slate-700 bg-slate-950/80 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-slate-100">{step.label}</p>
                      <p className="text-slate-400 text-sm">{info.detail || 'Waiting for step...'}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {info.status === 'running' && <span className="h-3 w-3 rounded-full bg-sky-400 animate-pulse" />}
                      <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${statusClass}`}>
                        {info.status}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        {pipelineResult && (
          <section className="rounded-3xl border border-slate-700 bg-slate-800/80 p-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold">Pipeline Result</h2>
                <p className="text-slate-400 text-sm">Expand each section to inspect generated resume content.</p>
              </div>
              <button
                onClick={() => setPipelineResult(null)}
                className="rounded-full border border-slate-600 px-3 py-1 text-sm text-slate-200 hover:bg-slate-700"
              >
                Clear
              </button>
            </div>
            <div className="space-y-4 text-slate-300 text-sm">
              {Object.entries(pipelineResult).map(([section, content]) => {
                const isOpen = openSections[section] ?? false
                return (
                  <div key={section} className="rounded-2xl border border-slate-700 bg-slate-950/50 p-4">
                    <button
                      type="button"
                      onClick={() => toggleSection(section)}
                      className="group flex w-full items-center justify-between gap-3 rounded-2xl px-3 py-3 text-left text-slate-100 transition-colors hover:bg-slate-900/80 hover:text-slate-50"
                    >
                      <span className="font-medium">{section.toUpperCase()}</span>
                      <span className="flex items-center justify-center text-slate-400 transition-colors group-hover:text-emerald-300">
                        <svg
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                        >
                          <path d="M6 9l6 6 6-6" />
                        </svg>
                      </span>
                    </button>
                    {isOpen && (
                      <div className="mt-4 overflow-auto rounded-xl bg-slate-900 p-4 text-slate-200">
                        <pre className="whitespace-pre-wrap break-words">{JSON.stringify(content, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
              <button
                onClick={() => {
                  const blob = new Blob([JSON.stringify(pipelineResult, null, 2)], { type: 'application/json' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = 'pipeline_result.json'
                  a.click()
                  URL.revokeObjectURL(url)
                }}
                className="rounded-full bg-slate-700 px-4 py-2 text-white hover:bg-slate-600"
              >
                Download JSON
              </button>
              <button
                onClick={downloadEnhancedResume}
                className="rounded-full bg-emerald-500 px-4 py-2 text-white hover:bg-emerald-400"
              >
                Download Enhanced Resume
              </button>
            </div>
          </section>
        )}
      </div>
    </main>
  )
}
