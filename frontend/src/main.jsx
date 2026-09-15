import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return null;
  return response.json();
}

function App() {
  const [documents, setDocuments] = useState([]);
  const [selected, setSelected] = useState([]);
  const [message, setMessage] = useState('');
  const [answer, setAnswer] = useState(null);
  const [mode, setMode] = useState('rag');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const readyDocuments = useMemo(() => documents.filter((doc) => doc.status === 'ready'), [documents]);

  async function loadDocuments() {
    try {
      const data = await request('/documents');
      setDocuments(data);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadDocuments();
    const timer = setInterval(loadDocuments, 3000);
    return () => clearInterval(timer);
  }, []);

  async function upload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError('');
    const form = new FormData();
    form.append('file', file);
    try {
      await request('/documents', { method: 'POST', body: form });
      await loadDocuments();
    } catch (err) {
      setError(err.message);
    }
    event.target.value = '';
  }

  async function ask() {
    if (!message.trim() || selected.length === 0) return;
    setBusy(true);
    setError('');
    try {
      const data = await request('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, document_ids: selected, mode }),
      });
      setAnswer(data);
      setMessage('');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function toggle(id) {
    setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  return (
    <main className="shell">
      <header>
        <div>
          <p className="eyebrow">GENAI ENGINEERING PROJECT</p>
          <h1>Document Intelligence</h1>
          <p className="sub">RAG + retrieval + citations + agentic tools</p>
        </div>
        <label className="upload">
          Upload document
          <input type="file" accept=".pdf,.txt,.md" onChange={upload} />
        </label>
      </header>

      {error && <div className="error">{error}</div>}

      <section className="grid">
        <aside className="panel">
          <div className="panel-title"><h2>Documents</h2><span>{readyDocuments.length} ready</span></div>
          {documents.length === 0 && <p className="muted">Upload a PDF, TXT, or Markdown file.</p>}
          {documents.map((doc) => (
            <label key={doc.id} className={`doc ${selected.includes(doc.id) ? 'selected' : ''}`}>
              <input type="checkbox" disabled={doc.status !== 'ready'} checked={selected.includes(doc.id)} onChange={() => toggle(doc.id)} />
              <div>
                <strong>{doc.filename}</strong>
                <small>{doc.status} · {doc.chunk_count} chunks</small>
              </div>
            </label>
          ))}
        </aside>

        <section className="panel chat">
          <div className="panel-title">
            <h2>Ask your documents</h2>
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="rag">RAG</option>
              <option value="agent">Agentic</option>
            </select>
          </div>
          <div className="answer">
            {answer ? <>
              <div className="answer-text">{answer.answer}</div>
              <div className="sources">
                <h3>Retrieved sources</h3>
                {answer.citations.map((source, index) => (
                  <div className="source" key={`${source.chunk_id}-${index}`}>
                    <b>[{index + 1}] {source.filename}</b>
                    <span>{source.page ? `Page ${source.page}` : 'Document'} · score {source.score?.toFixed?.(3) ?? 'n/a'}</span>
                    <p>{source.excerpt}</p>
                  </div>
                ))}
              </div>
            </> : <p className="muted">Select one or more ready documents and ask a question.</p>}
          </div>
          <div className="composer">
            <textarea value={message} onChange={(e) => setMessage(e.target.value)} placeholder="e.g. Compare the scheduling algorithms described in the selected documents." />
            <button disabled={busy || !message.trim() || selected.length === 0} onClick={ask}>{busy ? 'Thinking…' : 'Ask'}</button>
          </div>
        </section>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
