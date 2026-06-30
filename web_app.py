from __future__ import annotations

import os
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, Response, flash, jsonify, redirect, render_template_string, request, send_file, url_for

from core import DEFAULT_OUTPUT_NAME, build_transcript_document, extract_playlist_videos, parse_languages, transcripts_folder


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "transcripcion-playlist")

TASKS: dict[str, dict[str, Any]] = {}
TASKS_LOCK = threading.Lock()
GENERATED_FILES: dict[str, Path] = {}


def build_output_filename(raw_name: str) -> str:
    base_name = raw_name.strip() or DEFAULT_OUTPUT_NAME
    stem = Path(base_name).stem
    cleaned_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "transcripciones_playlist"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    return f"{cleaned_stem}_{timestamp}.txt"


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
            "preview": "",
            "download_url": "",
            "error_message": "",
            "playlist_url": playlist_url,
            "languages": languages,
            "filename": filename,
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
        "preview": task.get("preview", ""),
        "download_url": task.get("download_url", ""),
        "error_message": task.get("error_message", ""),
        "done": task.get("status") == "done",
        "error": task.get("status") == "error",
    }


PAGE_TEMPLATE = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transcriptor de playlist</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4efe6;
      --card: #fffaf3;
      --text: #1f2937;
      --muted: #6b7280;
      --accent: #b45309;
      --accent-strong: #92400e;
      --border: #eadfce;
      --success: #15803d;
      --error: #b91c1c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: Georgia, "Times New Roman", serif;
      background: radial-gradient(circle at top, #fff8ec 0, var(--bg) 45%, #ebe1d3 100%);
      color: var(--text);
      padding: 32px 16px;
    }
    .wrap { max-width: 960px; margin: 0 auto; }
    .hero { margin-bottom: 24px; padding: 8px 4px; }
    h1 { margin: 0 0 8px; font-size: clamp(2rem, 4vw, 3.6rem); line-height: 1; }
    .lead { margin: 0; color: var(--muted); font-size: 1.05rem; max-width: 70ch; }
    .card {
      background: rgba(255, 250, 243, 0.92);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 24px;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.08);
      backdrop-filter: blur(8px);
    }
    label { display: block; font-weight: 700; margin: 0 0 8px; }
    input {
      width: 100%;
      border: 1px solid #d8ccb8;
      border-radius: 14px;
      padding: 14px 16px;
      font: inherit;
      background: white;
      color: var(--text);
    }
    .grid { display: grid; gap: 16px; }
    .grid.two { grid-template-columns: 2fr 1fr; }
    .actions { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 18px; }
    button, .btn {
      display: inline-block;
      border: 0;
      border-radius: 999px;
      padding: 14px 20px;
      background: var(--accent);
      color: white;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
    }
    button:hover, .btn:hover { background: var(--accent-strong); }
    .note { color: var(--muted); font-size: 0.95rem; margin-top: 8px; }
    .flash {
      margin: 0 0 18px;
      padding: 14px 16px;
      border-radius: 14px;
      background: #fef3c7;
      border: 1px solid #f59e0b;
    }
    .result {
      white-space: pre-wrap;
      background: #0f172a;
      color: #e2e8f0;
      padding: 20px;
      border-radius: 16px;
      overflow-x: auto;
      max-height: 420px;
    }
    .footer { margin-top: 18px; color: var(--muted); font-size: 0.94rem; }
    .download-box {
      margin-top: 20px;
      padding: 16px;
      border: 1px solid #d8ccb8;
      border-radius: 16px;
      background: #fffdf8;
    }
    .download-title { margin: 0 0 10px; font-weight: 700; }
    .progress-shell {
      margin-top: 16px;
      padding: 14px;
      border-radius: 16px;
      border: 1px solid #d8ccb8;
      background: #f7f2ea;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.7; }
    }
    @keyframes slideIn {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes progress-stripes {
      0% { background-position: 0 0; }
      100% { background-position: 40px 0; }
    }
    .progress-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 14px;
      font-weight: 700;
      animation: slideIn 0.4s ease-out;
    }
    .progress-row span {
      font-size: 0.95rem;
      transition: color 0.3s ease;
    }
    #progressText { color: var(--accent); }
    #statusText { color: var(--muted); font-weight: 600; }
    progress {
      width: 100%;
      height: 24px;
      border-radius: 999px;
      overflow: hidden;
      appearance: none;
      -webkit-appearance: none;
      -moz-appearance: none;
    }
    progress::-webkit-progress-bar {
      background: linear-gradient(90deg, #eadfce 0%, #f0e6d2 100%);
      box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    progress::-webkit-progress-value {
      background: linear-gradient(90deg, #d97706 0%, #f59e0b 50%, #fbbf24 100%);
      background-size: 40px 40px;
      animation: progress-stripes 1.2s linear infinite;
      box-shadow: 0 0 10px rgba(217, 119, 6, 0.3);
    }
    progress::-moz-progress-bar {
      background: linear-gradient(90deg, #d97706 0%, #f59e0b 50%, #fbbf24 100%);
      background-size: 40px 40px;
      animation: progress-stripes 1.2s linear infinite;
      box-shadow: 0 0 10px rgba(217, 119, 6, 0.3);
    }
    .status-chip {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      margin-top: 14px;
      padding: 10px 14px;
      border-radius: 999px;
      background: #f3efe7;
      border: 1.5px solid #d8ccb8;
      font-weight: 700;
      font-size: 0.94rem;
      animation: slideIn 0.4s ease-out;
      transition: all 0.3s ease;
    }
    .status-chip::before {
      content: '';
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #f59e0b;
      animation: pulse 1.5s ease-in-out infinite;
    }
    .status-chip.success {
      background: #dcfce7;
      border-color: #86efac;
      color: var(--success);
    }
    .status-chip.success::before {
      background: var(--success);
      animation: none;
    }
    .status-chip.error {
      background: #fee2e2;
      border-color: #fecaca;
      color: var(--error);
    }
    .status-chip.error::before {
      background: var(--error);
      animation: none;
    }
    @media (max-width: 720px) {
      .grid.two { grid-template-columns: 1fr; }
      body { padding: 18px 12px; }
      .card { padding: 18px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>Transcriptor de playlist</h1>
      <p class="lead">Pega una playlist de YouTube, genera un archivo de texto ordenado con todas sus transcripciones y descárgalo desde el navegador. Sin instalar Python en tu equipo.</p>
    </div>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}
          <div class="flash">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="card">
      <form method="post" action="{{ url_for('generate') }}">
        <div class="grid">
          <div>
            <label for="playlist_url">URL de la playlist</label>
            <input id="playlist_url" name="playlist_url" type="url" placeholder="https://www.youtube.com/playlist?list=..." required value="{{ playlist_url or '' }}">
          </div>
          <div class="grid two">
            <div>
              <label for="languages">Idiomas preferidos</label>
              <input id="languages" name="languages" type="text" value="{{ languages or 'es,en' }}">
              <div class="note">Separados por coma. Ejemplo: es,en,es-419</div>
            </div>
            <div>
              <label for="filename">Nombre del archivo</label>
              <input id="filename" name="filename" type="text" value="{{ filename or default_filename }}">
              <div class="note">Se descargará como .txt</div>
            </div>
          </div>
        </div>

        <div class="actions">
          <button type="submit">Generar transcripciones</button>
        </div>
      </form>

      {% if task_id %}
        <div class="progress-shell">
          <div class="progress-row">
            <span id="progressText">{{ progress_text }}</span>
            <span id="statusText">{{ status_text }}</span>
          </div>
          <progress id="progressBar" value="{{ progress_percent }}" max="100"></progress>
          <div id="statusChip" class="status-chip {% if error_message %}error{% elif done %}success{% endif %}">
            <span id="statusChipText">{{ chip_text }}</span>
          </div>
        </div>
      {% endif %}

      {% if preview %}
        <div class="download-box">
          <div class="download-title">Resultado listo</div>
          <div class="result">{{ preview }}</div>
          <div class="footer">Puedes descargar el archivo directamente desde el enlace generado.</div>
          {% if download_url %}
            <p style="margin-top:16px"><a class="btn" href="{{ download_url }}">Descargar transcripción con fecha</a></p>
          {% endif %}
        </div>
      {% endif %}
    </div>
  </div>

  {% if task_id %}
  <script>
    const taskId = {{ task_id|tojson }};
    const stateUrl = {{ state_url|tojson }};
    const timer = setInterval(pollTask, 1000);

    async function pollTask() {
      try {
        const response = await fetch(stateUrl, { cache: 'no-store' });
        const data = await response.json();

        document.getElementById('progressText').textContent = data.progress_text || '0%';
        document.getElementById('statusText').textContent = data.status_text || '';
        document.getElementById('progressBar').value = data.progress_percent || 0;

        const chip = document.getElementById('statusChip');
        const chipText = document.getElementById('statusChipText');

        if (data.error) {
          chip.className = 'status-chip error';
          chipText.textContent = data.error_message || 'Hubo un error';
          clearInterval(timer);
          return;
        }

        if (data.done) {
          chip.className = 'status-chip success';
          chipText.textContent = 'Completado';
          if (data.preview) {
            let box = document.querySelector('.download-box');
            if (!box) {
              box = document.createElement('div');
              box.className = 'download-box';
              box.innerHTML = '<div class="download-title">Resultado listo</div><div class="result"></div><div class="footer">Puedes descargar el archivo directamente desde el enlace generado.</div><p style="margin-top:16px"></p>';
              document.querySelector('.card').appendChild(box);
            }
            box.querySelector('.result').textContent = data.preview;
            const linkContainer = box.querySelector('p');
            if (data.download_url) {
              linkContainer.innerHTML = '<a class="btn" href="' + data.download_url + '">Descargar transcripción con fecha</a>';
            }
          }
          clearInterval(timer);
          return;
        }

        chip.className = 'status-chip';
        chipText.textContent = 'Procesando';
      } catch (error) {
        console.error(error);
      }
    }

    pollTask();
  </script>
  {% endif %}
</body>
</html>
"""


def _render_page(**context: Any) -> str:
    return render_template_string(PAGE_TEMPLATE, **context)


def _run_task(task_id: str, playlist_url: str, languages: str, filename: str) -> None:
    try:
        preferred_languages = parse_languages(languages)
        _update_task(task_id, status="running", status_text="Leyendo videos de la playlist...", progress_percent=0, progress_text="0%")

        videos = extract_playlist_videos(playlist_url)
        if not videos:
            raise RuntimeError("No se encontraron videos en la playlist.")

        _update_task(task_id, status_text="Extrayendo transcripciones video por video...", progress_percent=0, progress_text=f"0% (0/{len(videos)})")

        def progress_callback(current: int, total: int, video: object) -> None:
            title = getattr(video, "title", "")
            percent = 0 if total <= 0 else min(100, int((current / total) * 100))
            _update_task(
                task_id,
                progress_percent=percent,
                progress_text=f"{percent}% ({current}/{total}) - {title}",
                status_text=f"Procesando: {title}",
            )

        content = build_transcript_document(playlist_url, videos, preferred_languages, progress_callback=progress_callback)
        output_folder = _default_output_folder()
        output_path = output_folder / build_output_filename(filename)
        output_path.write_text(content, encoding="utf-8")

        GENERATED_FILES[task_id] = output_path
        _update_task(
            task_id,
            status="done",
            status_text="Proceso terminado.",
            progress_percent=100,
            progress_text=f"100% ({len(videos)}/{len(videos)})",
            preview=content[:4000],
          download_url=f"/download/{task_id}",
        )
    except Exception as exc:  # noqa: BLE001
        _update_task(
            task_id,
            status="error",
            status_text="Hubo un error.",
            progress_percent=0,
            progress_text="0%",
            error_message=str(exc),
        )


@app.get("/")
def index() -> str:
    return _render_page(
        playlist_url="",
        languages="es,en",
        filename=DEFAULT_OUTPUT_NAME,
        preview="",
        download_url="",
        task_id="",
        state_url="",
        progress_text="",
        progress_percent=0,
        status_text="",
        chip_text="",
        error_message="",
        done=False,
        default_filename=DEFAULT_OUTPUT_NAME,
    )


@app.post("/generate")
def generate() -> Response | str:
    playlist_url = request.form.get("playlist_url", "").strip()
    languages = request.form.get("languages", "es,en").strip()
    filename = request.form.get("filename", DEFAULT_OUTPUT_NAME).strip() or DEFAULT_OUTPUT_NAME

    if not playlist_url:
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
        flash("No se encontró esa tarea. Intenta generar otra playlist.")
        return redirect(url_for("index"))

    return _render_page(
        playlist_url=task.get("playlist_url", ""),
        languages=task.get("languages", "es,en"),
        filename=task.get("filename", DEFAULT_OUTPUT_NAME),
        preview=task.get("preview", ""),
        download_url=task.get("download_url", ""),
        task_id=task_id,
        state_url=url_for("task_state", task_id=task_id),
        progress_text=task.get("progress_text", "0%"),
        progress_percent=task.get("progress_percent", 0),
        status_text=task.get("status_text", "Preparando tarea..."),
      chip_text="Error" if task.get("status") == "error" else ("Completado" if task.get("status") == "done" else "Procesando"),
        error_message=task.get("error_message", ""),
        done=task.get("status") == "done",
        default_filename=DEFAULT_OUTPUT_NAME,
    )


@app.get("/task/<task_id>/state")
def task_state(task_id: str) -> Response:
    return jsonify(_task_state_payload(task_id))


@app.get("/download/<token>")
def download(token: str) -> Response:
    output_path = GENERATED_FILES.get(token)
    if output_path is None:
        return Response("File not found", status=404)
    if not output_path.exists():
        return Response("File not found", status=404)
    return send_file(output_path, as_attachment=True, download_name=output_path.name)


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()