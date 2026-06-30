from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, redirect, render_template_string, request, send_file, url_for

from core import (
    DEFAULT_OUTPUT_NAME,
    build_output_filename,
    build_transcript_document,
    extract_playlist_title,
    extract_playlist_videos,
    parse_languages,
    save_transcript_file,
    transcripts_folder,
)


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "transcripcion-playlist-secret")

TASKS: dict[str, dict[str, Any]] = {}
TASKS_LOCK = threading.Lock()
GENERATED_FILES: dict[str, Path] = {}


def _default_output_folder() -> Path:
    output_folder = transcripts_folder()
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def _create_task(playlist_url: str, languages: str, filename: str) -> str:
    task_id = uuid.uuid4().hex
    with TASKS_LOCK:
        TASKS[task_id] = {
            "status": "queued",
            "status_text": "Preparando tarea...",
            "progress_percent": 0,
            "progress_text": "0%",
            "current_video": "",
            "preview": "",
            "download_url": "",
            "error_message": "",
            "playlist_url": playlist_url,
            "playlist_title": "",
            "languages": languages,
            "filename": filename,
            "output_filename": "",
        }
    return task_id


def _update_task(task_id: str, **changes: Any) -> None:
    with TASKS_LOCK:
        if task_id in TASKS:
            TASKS[task_id].update(changes)


def _get_task(task_id: str) -> dict[str, Any] | None:
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if task is None:
            return None
        return dict(task)


def _task_state_payload(task_id: str) -> dict[str, Any]:
    task = _get_task(task_id)
    if task is None:
        return {"exists": False}

    return {
        "exists": True,
        "status": task.get("status", "queued"),
        "status_text": task.get("status_text", ""),
        "progress_percent": task.get("progress_percent", 0),
        "progress_text": task.get("progress_text", "0%"),
        "current_video": task.get("current_video", ""),
        "playlist_title": task.get("playlist_title", ""),
        "preview": task.get("preview", ""),
        "download_url": task.get("download_url", ""),
        "error_message": task.get("error_message", ""),
        "output_filename": task.get("output_filename", ""),
        "done": task.get("status") == "done",
        "error": task.get("status") == "error",
    }


# ──────────────────────────────────────────────────────────────────────────────
# HTML Template — Premium modern design
# ──────────────────────────────────────────────────────────────────────────────

PAGE_TEMPLATE = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transcriptor de Playlists — YouTube</title>
  <meta name="description" content="Extrae las transcripciones de todos los videos de una playlist de YouTube en un solo archivo de texto ordenado.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg-primary: #0a0a0f;
      --bg-secondary: #12121a;
      --bg-card: rgba(255, 255, 255, 0.04);
      --bg-card-hover: rgba(255, 255, 255, 0.06);
      --bg-input: rgba(255, 255, 255, 0.06);
      --bg-input-focus: rgba(255, 255, 255, 0.1);
      --border: rgba(255, 255, 255, 0.08);
      --border-focus: rgba(251, 191, 36, 0.5);
      --text-primary: #f1f1f4;
      --text-secondary: #9ca3af;
      --text-muted: #6b7280;
      --accent: #f59e0b;
      --accent-hover: #fbbf24;
      --accent-glow: rgba(245, 158, 11, 0.25);
      --success: #22c55e;
      --success-bg: rgba(34, 197, 94, 0.1);
      --error: #ef4444;
      --error-bg: rgba(239, 68, 68, 0.1);
      --gradient-accent: linear-gradient(135deg, #f59e0b 0%, #ef4444 50%, #8b5cf6 100%);
      --radius-sm: 10px;
      --radius-md: 16px;
      --radius-lg: 24px;
      --radius-full: 999px;
      --shadow-card: 0 4px 24px rgba(0, 0, 0, 0.3), 0 0 0 1px var(--border);
      --shadow-glow: 0 0 40px var(--accent-glow);
      --transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }

    body {
      min-height: 100vh;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }

    /* Animated background gradient */
    body::before {
      content: '';
      position: fixed;
      top: -50%;
      left: -50%;
      width: 200%;
      height: 200%;
      background: radial-gradient(circle at 30% 20%, rgba(245, 158, 11, 0.06) 0%, transparent 40%),
                  radial-gradient(circle at 70% 60%, rgba(139, 92, 246, 0.04) 0%, transparent 40%),
                  radial-gradient(circle at 50% 80%, rgba(239, 68, 68, 0.03) 0%, transparent 40%);
      animation: bgFloat 20s ease-in-out infinite;
      pointer-events: none;
      z-index: 0;
    }

    @keyframes bgFloat {
      0%, 100% { transform: translate(0, 0) rotate(0deg); }
      33% { transform: translate(2%, -2%) rotate(1deg); }
      66% { transform: translate(-1%, 1%) rotate(-0.5deg); }
    }

    .container {
      position: relative;
      z-index: 1;
      max-width: 800px;
      margin: 0 auto;
      padding: 40px 20px 60px;
    }

    /* ── Header ── */
    .header {
      text-align: center;
      margin-bottom: 48px;
      animation: fadeInDown 0.6s ease-out;
    }

    @keyframes fadeInDown {
      from { opacity: 0; transform: translateY(-20px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .header__badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius-full);
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--accent);
      letter-spacing: 0.05em;
      text-transform: uppercase;
      margin-bottom: 20px;
    }

    .header__badge::before {
      content: '▶';
      font-size: 0.7rem;
    }

    .header h1 {
      font-size: clamp(2rem, 5vw, 3.2rem);
      font-weight: 900;
      line-height: 1.1;
      letter-spacing: -0.03em;
      background: var(--gradient-accent);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 12px;
    }

    .header p {
      font-size: 1.05rem;
      color: var(--text-secondary);
      max-width: 55ch;
      margin: 0 auto;
    }

    /* ── Card ── */
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 32px;
      box-shadow: var(--shadow-card);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      animation: fadeInUp 0.6s ease-out 0.15s both;
    }

    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(16px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* ── Form ── */
    .form-group {
      margin-bottom: 20px;
    }

    .form-group label {
      display: block;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-secondary);
      margin-bottom: 8px;
      letter-spacing: 0.02em;
    }

    .form-group input {
      width: 100%;
      padding: 14px 18px;
      background: var(--bg-input);
      border: 1.5px solid var(--border);
      border-radius: var(--radius-md);
      color: var(--text-primary);
      font-family: inherit;
      font-size: 0.95rem;
      transition: var(--transition);
      outline: none;
    }

    .form-group input::placeholder {
      color: var(--text-muted);
    }

    .form-group input:focus {
      background: var(--bg-input-focus);
      border-color: var(--border-focus);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }

    .form-hint {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 6px;
    }

    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    /* ── Buttons ── */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 14px 28px;
      border: none;
      border-radius: var(--radius-full);
      font-family: inherit;
      font-size: 0.95rem;
      font-weight: 700;
      cursor: pointer;
      transition: var(--transition);
      text-decoration: none;
      line-height: 1;
    }

    .btn--primary {
      background: var(--accent);
      color: #000;
      box-shadow: 0 4px 16px var(--accent-glow);
    }

    .btn--primary:hover {
      background: var(--accent-hover);
      box-shadow: var(--shadow-glow);
      transform: translateY(-1px);
    }

    .btn--primary:active {
      transform: translateY(0);
    }

    .btn--ghost {
      background: var(--bg-card);
      color: var(--text-primary);
      border: 1px solid var(--border);
    }

    .btn--ghost:hover {
      background: var(--bg-card-hover);
      border-color: rgba(255, 255, 255, 0.15);
    }

    .btn--success {
      background: var(--success);
      color: #000;
      box-shadow: 0 4px 16px rgba(34, 197, 94, 0.25);
    }

    .btn--success:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 24px rgba(34, 197, 94, 0.35);
    }

    .actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 24px;
    }

    /* ── Progress Panel ── */
    .progress-panel {
      margin-top: 28px;
      padding: 24px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      animation: fadeInUp 0.4s ease-out;
    }

    .progress-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .progress-header__percent {
      font-size: 1.8rem;
      font-weight: 800;
      color: var(--accent);
      letter-spacing: -0.03em;
      font-variant-numeric: tabular-nums;
    }

    .progress-header__status {
      font-size: 0.85rem;
      color: var(--text-secondary);
      text-align: right;
      max-width: 50%;
    }

    .progress-track {
      width: 100%;
      height: 8px;
      background: rgba(255, 255, 255, 0.06);
      border-radius: var(--radius-full);
      overflow: hidden;
      position: relative;
    }

    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #f59e0b, #fbbf24, #f59e0b);
      background-size: 200% 100%;
      border-radius: var(--radius-full);
      transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
      animation: progressShimmer 2s linear infinite;
      box-shadow: 0 0 12px var(--accent-glow);
    }

    @keyframes progressShimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .progress-video {
      margin-top: 12px;
      font-size: 0.85rem;
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .progress-video strong {
      color: var(--text-secondary);
    }

    /* ── Status Chip ── */
    .status-chip {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin-top: 16px;
      padding: 8px 16px;
      border-radius: var(--radius-full);
      font-size: 0.85rem;
      font-weight: 600;
      border: 1px solid var(--border);
      background: var(--bg-card);
      animation: fadeInUp 0.3s ease-out;
    }

    .status-chip__dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
      animation: pulse 1.5s ease-in-out infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(0.85); }
    }

    .status-chip--success {
      border-color: rgba(34, 197, 94, 0.3);
      background: var(--success-bg);
      color: var(--success);
    }

    .status-chip--success .status-chip__dot {
      background: var(--success);
      animation: none;
    }

    .status-chip--error {
      border-color: rgba(239, 68, 68, 0.3);
      background: var(--error-bg);
      color: var(--error);
    }

    .status-chip--error .status-chip__dot {
      background: var(--error);
      animation: none;
    }

    /* ── Result Panel ── */
    .result-panel {
      margin-top: 28px;
      animation: fadeInUp 0.5s ease-out;
    }

    .result-panel__header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .result-panel__title {
      font-size: 1.1rem;
      font-weight: 700;
    }

    .result-panel__filename {
      font-size: 0.8rem;
      color: var(--text-muted);
      font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
      background: var(--bg-card);
      padding: 4px 10px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border);
    }

    .result-preview {
      background: #0d1117;
      color: #c9d1d9;
      padding: 20px;
      border-radius: var(--radius-md);
      border: 1px solid rgba(255, 255, 255, 0.06);
      font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
      font-size: 0.82rem;
      line-height: 1.7;
      max-height: 360px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .result-preview::-webkit-scrollbar {
      width: 6px;
    }

    .result-preview::-webkit-scrollbar-track {
      background: transparent;
    }

    .result-preview::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 3px;
    }

    .result-actions {
      display: flex;
      gap: 12px;
      margin-top: 20px;
      flex-wrap: wrap;
    }

    /* ── Flash / Error ── */
    .flash-message {
      padding: 14px 18px;
      border-radius: var(--radius-md);
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.3);
      color: var(--accent);
      font-size: 0.9rem;
      font-weight: 500;
      margin-bottom: 20px;
      animation: fadeInUp 0.3s ease-out;
    }

    .error-panel {
      margin-top: 20px;
      padding: 18px;
      border-radius: var(--radius-md);
      background: var(--error-bg);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: var(--error);
      font-size: 0.9rem;
      animation: fadeInUp 0.3s ease-out;
    }

    .error-panel strong {
      display: block;
      margin-bottom: 6px;
    }

    /* ── Footer ── */
    .footer {
      text-align: center;
      margin-top: 48px;
      color: var(--text-muted);
      font-size: 0.82rem;
    }

    .footer a {
      color: var(--accent);
      text-decoration: none;
    }

    .footer a:hover {
      text-decoration: underline;
    }

    /* ── Spinner ── */
    .spinner {
      width: 18px;
      height: 18px;
      border: 2.5px solid rgba(0, 0, 0, 0.15);
      border-top-color: #000;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    /* ── Responsive ── */
    @media (max-width: 640px) {
      .container { padding: 24px 16px 40px; }
      .card { padding: 20px; }
      .form-row { grid-template-columns: 1fr; }
      .progress-header { flex-direction: column; align-items: flex-start; gap: 4px; }
      .progress-header__status { text-align: left; max-width: 100%; }
      .result-panel__header { flex-direction: column; align-items: flex-start; gap: 8px; }
    }
  </style>
</head>
<body>
  <div class="container">
    <header class="header">
      <div class="header__badge">YouTube Transcriptor</div>
      <h1>Transcriptor de Playlists</h1>
      <p>Extrae las transcripciones de una playlist de YouTube completa en un solo archivo de texto ordenado.</p>
    </header>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}
          <div class="flash-message">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="card" id="mainCard">
      <form method="post" action="{{ url_for('generate') }}" id="mainForm">
        <div class="form-group">
          <label for="playlist_url">URL de la playlist</label>
          <input id="playlist_url" name="playlist_url" type="url"
                 placeholder="https://www.youtube.com/playlist?list=PLxxxxxx"
                 required value="{{ playlist_url or '' }}">
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="languages">Idiomas preferidos</label>
            <input id="languages" name="languages" type="text"
                   value="{{ languages or 'es,en' }}">
            <div class="form-hint">Separados por coma · Ej: es,en,es-419</div>
          </div>
          <div class="form-group">
            <label for="filename">Nombre del archivo (opcional)</label>
            <input id="filename" name="filename" type="text"
                   value="{{ filename or '' }}"
                   placeholder="Se detecta automáticamente">
            <div class="form-hint">Si lo dejas vacío, se usa el nombre de la playlist</div>
          </div>
        </div>

        <div class="actions">
          <button type="submit" class="btn btn--primary" id="submitBtn">
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path d="M12 3v18m0-18l-4 4m4-4l4 4M5 21h14"/></svg>
            Generar transcripciones
          </button>
        </div>
      </form>

      <!-- Progress panel (injected via JS or server) -->
      <div id="progressPanel" style="display:none"></div>

      <!-- Result panel (injected via JS) -->
      <div id="resultPanel" style="display:none"></div>

      <!-- Error panel -->
      <div id="errorPanel" style="display:none"></div>
    </div>

    <footer class="footer">
      Transcriptor de Playlists &middot; Hecho con Flask + yt-dlp + youtube-transcript-api
    </footer>
  </div>

  {% if task_id %}
  <script>
    const TASK_ID = {{ task_id|tojson }};
    const STATE_URL = {{ state_url|tojson }};
    let polling = null;
    let lastPercent = -1;

    function init() {
      document.getElementById('submitBtn').disabled = true;
      document.getElementById('submitBtn').innerHTML = '<span class="spinner"></span> Procesando...';
      showProgressPanel();
      polling = setInterval(pollState, 800);
      pollState();
    }

    function showProgressPanel() {
      const panel = document.getElementById('progressPanel');
      panel.style.display = 'block';
      panel.innerHTML = `
        <div class="progress-panel">
          <div class="progress-header">
            <span class="progress-header__percent" id="pPercent">0%</span>
            <span class="progress-header__status" id="pStatus">Iniciando...</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" id="pFill" style="width:0%"></div>
          </div>
          <div class="progress-video" id="pVideo"></div>
          <div class="status-chip" id="pChip">
            <span class="status-chip__dot"></span>
            <span id="pChipText">Procesando</span>
          </div>
        </div>`;
    }

    async function pollState() {
      try {
        const res = await fetch(STATE_URL, { cache: 'no-store' });
        const d = await res.json();

        if (!d.exists) { stopPolling(); return; }

        // Update progress
        const pct = d.progress_percent || 0;
        document.getElementById('pPercent').textContent = d.progress_text || (pct + '%');
        document.getElementById('pStatus').textContent = d.status_text || '';
        document.getElementById('pFill').style.width = pct + '%';

        if (d.current_video) {
          document.getElementById('pVideo').innerHTML = 'Procesando: <strong>' + escapeHtml(d.current_video) + '</strong>';
        }

        if (d.playlist_title && pct > 0) {
          const titleEl = document.getElementById('pVideo');
          if (!titleEl.dataset.titleShown) {
            titleEl.dataset.titleShown = '1';
          }
        }

        // Error
        if (d.error) {
          stopPolling();
          const chip = document.getElementById('pChip');
          chip.className = 'status-chip status-chip--error';
          document.getElementById('pChipText').textContent = 'Error';
          document.getElementById('pFill').style.background = 'var(--error)';

          const errPanel = document.getElementById('errorPanel');
          errPanel.style.display = 'block';
          errPanel.innerHTML = `<div class="error-panel"><strong>⚠ Error durante el proceso</strong>${escapeHtml(d.error_message)}</div>`;

          resetButton();
          return;
        }

        // Done
        if (d.done) {
          stopPolling();
          document.getElementById('pPercent').textContent = '100%';
          document.getElementById('pFill').style.width = '100%';
          document.getElementById('pFill').style.animation = 'none';
          document.getElementById('pFill').style.background = 'var(--success)';
          document.getElementById('pFill').style.boxShadow = '0 0 12px rgba(34,197,94,0.3)';

          const chip = document.getElementById('pChip');
          chip.className = 'status-chip status-chip--success';
          document.getElementById('pChipText').textContent = '✓ Completado';

          // Show result panel
          if (d.preview || d.download_url) {
            const resultPanel = document.getElementById('resultPanel');
            resultPanel.style.display = 'block';
            const filenameDisplay = d.output_filename ? `<span class="result-panel__filename">${escapeHtml(d.output_filename)}</span>` : '';
            resultPanel.innerHTML = `
              <div class="result-panel">
                <div class="result-panel__header">
                  <span class="result-panel__title">✓ Transcripción lista</span>
                  ${filenameDisplay}
                </div>
                ${d.preview ? `<div class="result-preview">${escapeHtml(d.preview)}</div>` : ''}
                <div class="result-actions">
                  ${d.download_url ? `<a class="btn btn--success" href="${d.download_url}">⬇ Descargar archivo</a>` : ''}
                  <button class="btn btn--ghost" onclick="startNew()">+ Nueva transcripción</button>
                </div>
              </div>`;
          }

          resetButton();
          return;
        }
      } catch (e) {
        console.error('Poll error:', e);
      }
    }

    function stopPolling() {
      if (polling) { clearInterval(polling); polling = null; }
    }

    function resetButton() {
      const btn = document.getElementById('submitBtn');
      btn.disabled = false;
      btn.innerHTML = `<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path d="M12 3v18m0-18l-4 4m4-4l4 4M5 21h14"/></svg> Generar transcripciones`;
    }

    function startNew() {
      document.getElementById('playlist_url').value = '';
      document.getElementById('filename').value = '';
      document.getElementById('progressPanel').style.display = 'none';
      document.getElementById('resultPanel').style.display = 'none';
      document.getElementById('errorPanel').style.display = 'none';
      document.getElementById('playlist_url').focus();
      // Remove the task_id from the page so a fresh form submit goes to /generate
      const form = document.getElementById('mainForm');
      form.action = '/generate';
      resetButton();
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    init();
  </script>
  {% endif %}
</body>
</html>
"""


def _render_page(**context: Any) -> str:
    return render_template_string(PAGE_TEMPLATE, **context)


def _run_task(task_id: str, playlist_url: str, languages: str, filename: str) -> None:
    """Background worker that processes a playlist transcription task."""
    try:
        preferred_languages = parse_languages(languages)

        # Step 1: Get playlist title
        _update_task(task_id, status="running", status_text="Obteniendo nombre de la playlist...", progress_percent=0, progress_text="0%")
        playlist_title = extract_playlist_title(playlist_url)
        if playlist_title:
            _update_task(task_id, playlist_title=playlist_title, status_text=f"Playlist: {playlist_title}")

        # Step 2: Extract video list
        _update_task(task_id, status_text="Leyendo videos de la playlist...")
        videos = extract_playlist_videos(playlist_url)
        if not videos:
            raise RuntimeError("No se encontraron videos en la playlist.")

        _update_task(
            task_id,
            status_text=f"Extrayendo transcripciones ({len(videos)} videos)...",
            progress_percent=0,
            progress_text=f"0% (0/{len(videos)})",
        )

        # Step 3: Build transcript document with progress
        def progress_callback(current: int, total: int, video: object) -> None:
            title = getattr(video, "title", "")
            percent = 0 if total <= 0 else min(100, int((current / total) * 100))
            _update_task(
                task_id,
                progress_percent=percent,
                progress_text=f"{percent}% ({current}/{total})",
                current_video=title,
                status_text=f"Video {current}/{total}",
            )

        content = build_transcript_document(
            playlist_url, videos, preferred_languages,
            playlist_title=playlist_title,
            progress_callback=progress_callback,
        )

        # Step 4: Determine output filename
        # Priority: user-specified filename > playlist title > default
        if filename and filename != DEFAULT_OUTPUT_NAME:
            final_filename = build_output_filename(filename)
        elif playlist_title:
            final_filename = build_output_filename(playlist_title)
        else:
            final_filename = build_output_filename()

        output_folder = _default_output_folder()
        output_path = output_folder / final_filename
        save_transcript_file(output_path, content)

        GENERATED_FILES[task_id] = output_path

        _update_task(
            task_id,
            status="done",
            status_text="¡Proceso completado!",
            progress_percent=100,
            progress_text=f"100% ({len(videos)}/{len(videos)})",
            preview=content[:4000],
            download_url=f"/download/{task_id}",
            output_filename=final_filename,
        )
    except Exception as exc:  # noqa: BLE001
        _update_task(
            task_id,
            status="error",
            status_text="Error durante el proceso.",
            progress_percent=0,
            progress_text="0%",
            error_message=str(exc),
        )


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/")
def index() -> str:
    return _render_page(
        playlist_url="",
        languages="es,en",
        filename="",
        task_id="",
        state_url="",
        default_filename=DEFAULT_OUTPUT_NAME,
    )


@app.post("/generate")
def generate() -> Response | str:
    playlist_url = request.form.get("playlist_url", "").strip()
    languages = request.form.get("languages", "es,en").strip()
    filename = request.form.get("filename", "").strip()

    if not playlist_url:
        from flask import flash
        flash("Pega una URL de playlist antes de generar el archivo.")
        return redirect(url_for("index"))

    task_id = _create_task(playlist_url, languages, filename)
    worker = threading.Thread(target=_run_task, args=(task_id, playlist_url, languages, filename), daemon=True)
    worker.start()

    return redirect(url_for("task_view", task_id=task_id))


@app.get("/task/<task_id>")
def task_view(task_id: str) -> str:
    task = _get_task(task_id)
    if task is None:
        from flask import flash
        flash("No se encontró esa tarea. Intenta generar otra playlist.")
        return redirect(url_for("index"))

    return _render_page(
        playlist_url=task.get("playlist_url", ""),
        languages=task.get("languages", "es,en"),
        filename=task.get("filename", ""),
        task_id=task_id,
        state_url=url_for("task_state", task_id=task_id),
        default_filename=DEFAULT_OUTPUT_NAME,
    )


@app.get("/task/<task_id>/state")
def task_state(task_id: str) -> Response:
    return jsonify(_task_state_payload(task_id))


@app.get("/download/<token>")
def download(token: str) -> Response:
    output_path = GENERATED_FILES.get(token)
    if output_path is None or not output_path.exists():
        return Response("Archivo no encontrado.", status=404)
    return send_file(output_path, as_attachment=True, download_name=output_path.name)


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    print(f"\\n  🎬 Transcriptor de Playlists iniciado")
    print(f"  → Abre tu navegador en: http://localhost:{port}\\n")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()