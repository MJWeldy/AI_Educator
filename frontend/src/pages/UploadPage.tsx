import { useRef, useState, type DragEvent } from 'react'
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

// Recursively read files out of a drag-and-drop, expanding any dropped folder
// into its files while preserving each file's path (so the backend can group
// the upload by folder). Falls back to a flat file list when the entries API
// is unavailable.
async function filesFromDataTransfer(dt: DataTransfer): Promise<File[]> {
  const entries = [...(dt.items || [])]
    .map((it) => (it.webkitGetAsEntry ? it.webkitGetAsEntry() : null))
    .filter(Boolean) as FileSystemEntry[]
  if (!entries.length) return Array.from(dt.files || [])
  const out: File[] = []
  const readAll = (reader: FileSystemDirectoryReader): Promise<FileSystemEntry[]> =>
    new Promise((resolve) => {
      const acc: FileSystemEntry[] = []
      const step = () =>
        reader.readEntries((batch) => {
          if (!batch.length) return resolve(acc)
          acc.push(...batch)
          step()
        }, () => resolve(acc))
      step()
    })
  const walk = async (entry: FileSystemEntry, prefix: string) => {
    if (entry.isFile) {
      const file = await new Promise<File>((res, rej) =>
        (entry as FileSystemFileEntry).file(res, rej),
      )
      try {
        Object.defineProperty(file, 'webkitRelativePath', { value: prefix + entry.name, configurable: true })
      } catch {
        /* read-only in some browsers */
      }
      out.push(file)
    } else if (entry.isDirectory) {
      const children = await readAll((entry as FileSystemDirectoryEntry).createReader())
      for (const c of children) await walk(c, prefix + entry.name + '/')
    }
  }
  for (const e of entries) await walk(e, '')
  return out
}

export default function UploadPage() {
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const folderRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data: docs } = useQuery({
    queryKey: ['documents'],
    queryFn: () => api<DocumentOut[]>('/api/documents'),
    refetchInterval: (q) =>
      (q.state.data ?? []).some((d) => ACTIVE.includes(d.status)) ? 2500 : false,
  })

  const upload = async (files: File[]) => {
    if (!files.length) return
    setUploading(true)
    setError(null)
    try {
      const form = new FormData()
      for (const f of files) {
        const rel = (f as File & { webkitRelativePath?: string }).webkitRelativePath
        form.append('files', f, rel || f.name)
      }
      const res = await fetch('/api/documents', { method: 'POST', body: form })
      if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
      if (folderRef.current) folderRef.current.value = ''
    }
  }

  const onDrop = async (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    if (uploading) return
    upload(await filesFromDataTransfer(e.dataTransfer))
  }

  return (
    <>
      <div className="page-kicker rise">Bring your own material</div>
      <h1 className="page-title rise rise-1">Upload a book or a folder</h1>
      <p className="page-sub rise rise-2">
        Drop in a PDF — or a whole folder of PDFs, notes, and markdown — and the app reads
        it, derives a topic graph welded into your existing curriculum, writes lessons and
        practice problems, and (after your review) teaches it with the same
        mastery-and-review engine. Works with open textbooks like OpenStax and Open
        University course PDFs.
      </p>

      <div className="rise rise-3" style={{ marginBottom: 30 }}>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".pdf,.txt,.md,.markdown,.rst,.tex,.py,.js,.ts,.tsx,.java,.c,.h,.cpp,.go,.rs,.rb,application/pdf,text/plain,text/markdown"
          style={{ display: 'none' }}
          onChange={(e) => upload(Array.from(e.target.files ?? []))}
        />
        <input
          ref={folderRef}
          type="file"
          // @ts-expect-error non-standard directory-picker attributes
          webkitdirectory=""
          directory=""
          multiple
          style={{ display: 'none' }}
          onChange={(e) => upload(Array.from(e.target.files ?? []))}
        />
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className={`upload-drop${dragOver ? ' over' : ''}`}
          style={{
            border: `1px dashed ${dragOver ? 'var(--accent, #7a5)' : 'rgba(0,0,0,0.2)'}`,
            borderRadius: 12,
            padding: '26px 20px',
            textAlign: 'center',
            background: dragOver ? 'rgba(120,160,90,0.06)' : 'transparent',
            transition: 'background .15s, border-color .15s',
          }}
        >
          <p className="muted" style={{ marginBottom: 14, fontSize: 14 }}>
            {uploading ? 'Uploading…' : 'Drag a file or folder here, or'}
          </p>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button className="btn" disabled={uploading} onClick={() => fileRef.current?.click()}>
              Choose files →
            </button>
            <button
              className="btn secondary"
              disabled={uploading}
              onClick={() => folderRef.current?.click()}
            >
              Choose a folder →
            </button>
          </div>
        </div>
        {error && <div className="feedback-banner bad" style={{ marginTop: 14 }}>{error}</div>}
        <p className="muted" style={{ fontSize: 13, marginTop: 12 }}>
          A folder becomes one course — each file its own chapter. Ingestion runs in the
          background and can take a while on a local model — Claude (Settings) is faster and
          better at math-heavy books. Safe to close the page.
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
                <button
                  className="btn secondary danger"
                  style={{ padding: '6px 12px', fontSize: 12, marginLeft: 8 }}
                  title="Delete this book, its course, and all progress on it"
                  onClick={async () => {
                    if (
                      !window.confirm(
                        `Delete “${d.title || d.filename}”?\n\nThis removes the book, its derived course and topics, and any progress on them. This cannot be undone.`,
                      )
                    )
                      return
                    await api(`/api/documents/${d.id}`, { method: 'DELETE' })
                    queryClient.invalidateQueries()
                  }}
                >
                  Delete
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
