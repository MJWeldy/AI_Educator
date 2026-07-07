import { useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export interface DocumentOut {
  id: number
  filename: string
  title: string
  status: string
  error: string | null
  page_count: number
  topic_count: number
  progress: { stage?: string; current?: number; total?: number; message?: string; job_status?: string } | null
}

const ACTIVE = ['uploaded', 'extracting', 'segmenting', 'deriving', 'generating']

export default function UploadPage() {
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data: docs } = useQuery({
    queryKey: ['documents'],
    queryFn: () => api<DocumentOut[]>('/api/documents'),
    refetchInterval: (q) =>
      (q.state.data ?? []).some((d) => ACTIVE.includes(d.status)) ? 2500 : false,
  })

  const upload = async (file: File) => {
    setUploading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/documents', { method: 'POST', body: form })
      if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <>
      <div className="page-kicker rise">Bring your own book</div>
      <h1 className="page-title rise rise-1">Upload a textbook</h1>
      <p className="page-sub rise rise-2">
        Drop in a PDF — the app reads it, derives a topic graph welded into your existing
        curriculum, writes lessons and practice problems, and (after your review) teaches
        it with the same mastery-and-review engine. Works with open textbooks like
        OpenStax and Open University course PDFs.
      </p>

      <div className="rise rise-3" style={{ marginBottom: 30 }}>
        <input
          ref={fileRef}
          type="file"
          accept="application/pdf"
          style={{ display: 'none' }}
          onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
        />
        <button className="btn" disabled={uploading} onClick={() => fileRef.current?.click()}>
          {uploading ? 'Uploading…' : 'Choose a PDF →'}
        </button>
        {error && <div className="feedback-banner bad" style={{ marginTop: 14 }}>{error}</div>}
        <p className="muted" style={{ fontSize: 13, marginTop: 12 }}>
          Ingestion runs in the background and can take a while on a local model — Claude
          (Settings) is faster and better at math-heavy books. Safe to close the page.
        </p>
      </div>

      {docs && docs.length > 0 && (
        <div className="rise rise-4">
          <h3 style={{ marginBottom: 12 }}>Your books</h3>
          {docs.map((d) => (
            <div key={d.id} className="task-row" style={{ cursor: 'default' }}>
              <span className={`task-chip ${d.status === 'published' ? 'review' : d.status === 'failed' ? 'quiz' : 'lesson'}`}>
                {d.status}
              </span>
              <div style={{ minWidth: 0 }}>
                <div className="task-title">{d.title || d.filename}</div>
                <div className="mono muted" style={{ fontSize: 11 }}>
                  {d.page_count > 0 && `${d.page_count} pages · `}
                  {d.topic_count > 0 && `${d.topic_count} topics · `}
                  {ACTIVE.includes(d.status) && d.progress?.stage && (
                    <>
                      {d.progress.stage}
                      {d.progress.total ? ` ${d.progress.current}/${d.progress.total}` : ''}
                      {d.progress.message ? ` — ${d.progress.message}` : ''}
                    </>
                  )}
                  {d.status === 'failed' && (d.error?.split('\n')[0] ?? 'failed')}
                </div>
              </div>
              <span className="task-xp">
                {d.progress?.job_status === 'failed' && !['review', 'published'].includes(d.status) && (
                  <button
                    className="btn secondary"
                    style={{ padding: '6px 14px', fontSize: 12 }}
                    onClick={async () => {
                      await api(`/api/documents/${d.id}/retry`, { method: 'POST' })
                      queryClient.invalidateQueries({ queryKey: ['documents'] })
                    }}
                  >
                    Retry
                  </button>
                )}
                {(d.status === 'review' || d.status === 'published') && (
                  <Link to={`/documents/${d.id}`} className="btn secondary" style={{ padding: '6px 14px', fontSize: 12 }}>
                    {d.status === 'review' ? 'Review & publish' : 'View'}
                  </Link>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
