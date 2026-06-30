from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Button, Entry, Frame, Label, Scrollbar, StringVar, Text, Tk, filedialog, messagebox, ttk

from core import DEFAULT_OUTPUT_NAME, PlaylistVideo, build_output_filename, build_transcript_document, extract_playlist_title, extract_playlist_videos, parse_languages, sanitize_filename, save_transcript_file, transcripts_folder


APP_TITLE = "Transcripción de playlist de YouTube"
DEFAULT_LANGUAGES = "es,en"


class TranscriptApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("860x620")
        self.root.minsize(760, 540)

        self.status_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.is_running = False
        self.total_videos = 0

        self.playlist_url_var = StringVar()
        self.output_path_var = StringVar(value=str(self._default_output_path()))
        self.languages_var = StringVar(value=DEFAULT_LANGUAGES)

        self._build_ui()
        self.root.after(100, self._poll_status_queue)

    def _build_ui(self) -> None:
        self.root.configure(padx=16, pady=16)

        title = Label(self.root, text=APP_TITLE, font=("Segoe UI", 18, "bold"))
        title.pack(anchor="w")

        subtitle = Label(
            self.root,
            text="Pega el enlace de una playlist y exporta las transcripciones en el orden del listado.",
            font=("Segoe UI", 10),
        )
        subtitle.pack(anchor="w", pady=(4, 14))

        form = Frame(self.root)
        form.pack(fill=X)

        self._add_field(form, "URL de la playlist", self.playlist_url_var, hint="Pega aquí el enlace completo de la playlist.")
        self._add_path_field(form, "Archivo de salida", self.output_path_var)
        self._add_field(form, "Idiomas preferidos", self.languages_var, hint="Ejemplo: es,en,es-419")

        actions = Frame(self.root)
        actions.pack(fill=X, pady=(8, 10))

        self.export_button = Button(actions, text="Extraer transcripciones", command=self.start_export, height=2)
        self.export_button.pack(side=LEFT)

        self.open_output_button = Button(actions, text="Abrir carpeta de salida", command=self.open_output_folder)
        self.open_output_button.pack(side=LEFT, padx=(10, 0))

        self.status_label = Label(self.root, text="Listo.", anchor="w", font=("Segoe UI", 10, "italic"))
        self.status_label.pack(fill=X, pady=(0, 8))

        self.progress_label = Label(self.root, text="Progreso: 0%", anchor="w", font=("Segoe UI", 10, "bold"))
        self.progress_label.pack(fill=X, pady=(0, 8))

        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", mode="determinate", maximum=100)
        self.progress_bar.pack(fill=X, pady=(0, 10))

        log_frame = Frame(self.root)
        log_frame.pack(fill=BOTH, expand=True)

        self.log_text = Text(log_frame, wrap="word", height=20)
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)

        self.scrollbar = Scrollbar(log_frame, command=self.log_text.yview)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.log_text.configure(yscrollcommand=self.scrollbar.set)

    def _add_field(self, parent: Frame, label_text: str, variable: StringVar, hint: str | None = None) -> None:
        container = Frame(parent)
        container.pack(fill=X, pady=(0, 10))

        label = Label(container, text=label_text, anchor="w")
        label.pack(fill=X)

        entry = Entry(container, textvariable=variable)
        entry.pack(fill=X, pady=(4, 0))

        if hint:
            helper = Label(container, text=hint, anchor="w", font=("Segoe UI", 9, "italic"))
            helper.pack(fill=X, pady=(3, 0))

    def _add_path_field(self, parent: Frame, label_text: str, variable: StringVar) -> None:
        container = Frame(parent)
        container.pack(fill=X, pady=(0, 10))

        label = Label(container, text=label_text, anchor="w")
        label.pack(fill=X)

        row_frame = Frame(container)
        row_frame.pack(fill=X, pady=(4, 0))

        entry = Entry(row_frame, textvariable=variable)
        entry.pack(side=LEFT, fill=X, expand=True)

        browse = Button(row_frame, text="Elegir...", command=self.choose_output_path)
        browse.pack(side=RIGHT, padx=(8, 0))

    def log(self, message: str) -> None:
        self.log_text.insert(END, message + "\n")
        self.log_text.see(END)

    def set_status(self, message: str) -> None:
        self.status_label.configure(text=message)

    def set_progress(self, current: int, total: int, video_title: str | None = None) -> None:
        if total <= 0:
            percentage = 0
        else:
            percentage = min(100, int((current / total) * 100))

        self.progress_bar.configure(value=percentage)

        if video_title:
            self.progress_label.configure(text=f"Progreso: {percentage}% ({current}/{total}) - {video_title}")
        else:
            self.progress_label.configure(text=f"Progreso: {percentage}% ({current}/{total})")

    def _default_output_path(self) -> Path:
        output_folder = transcripts_folder()
        output_folder.mkdir(parents=True, exist_ok=True)
        return output_folder / build_output_filename()

    def choose_output_path(self) -> None:
        default_folder = transcripts_folder()
        default_folder.mkdir(parents=True, exist_ok=True)
        file_path = filedialog.asksaveasfilename(
            title="Guardar transcripciones como",
            defaultextension=".txt",
            filetypes=[("Archivo de texto", "*.txt"), ("Todos los archivos", "*.*")],
            initialdir=str(default_folder),
            initialfile=Path(self.output_path_var.get()).name,
        )
        if file_path:
            self.output_path_var.set(str(default_folder / Path(file_path).name))

    def open_output_folder(self) -> None:
        folder = transcripts_folder()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            import os

            os.startfile(folder)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", f"No se pudo abrir la carpeta: {exc}")

    def start_export(self) -> None:
        if self.is_running:
            return

        playlist_url = self.playlist_url_var.get().strip()
        if not playlist_url:
            messagebox.showwarning("Falta la URL", "Pega primero el enlace de la playlist.")
            return

        output_path = self.output_path_var.get().strip()
        if not output_path:
            messagebox.showwarning("Falta la salida", "Elige un archivo de salida.")
            return

        preferred_languages = parse_languages(self.languages_var.get())
        self.total_videos = 0
        self.set_progress(0, 0)

        self.is_running = True
        self.export_button.configure(state="disabled")
        self.set_status("Extrayendo información de la playlist...")
        self.log("Iniciando exportación...")

        worker = threading.Thread(
            target=self._export_worker,
            args=(playlist_url, output_path, preferred_languages),
            daemon=True,
        )
        worker.start()

    def _export_worker(self, playlist_url: str, output_path: str, preferred_languages: list[str]) -> None:
        try:
            self.status_queue.put(("log", "Leyendo videos de la playlist..."))

            # Get playlist title for the filename
            self.status_queue.put(("status", "Obteniendo nombre de la playlist..."))
            playlist_title = extract_playlist_title(playlist_url)
            if playlist_title:
                self.status_queue.put(("log", f"Playlist: {playlist_title}"))

            videos = extract_playlist_videos(playlist_url)
            if not videos:
                raise RuntimeError("No se encontraron videos en la playlist.")

            self.status_queue.put(("log", f"Videos detectados: {len(videos)}"))
            self.status_queue.put(("status", "Extrayendo transcripciones video por video..."))
            self.status_queue.put(("progress", f"0|{len(videos)}|Iniciando"))

            def progress_callback(current: int, total: int, video: PlaylistVideo) -> None:
                video_title = video.title
                self.status_queue.put(("progress", f"{current}|{total}|{video_title or ''}"))

            content = build_transcript_document(playlist_url, videos, preferred_languages, playlist_title=playlist_title, progress_callback=progress_callback)

            # Use playlist title as filename, falling back to what user set
            if playlist_title:
                final_filename = build_output_filename(playlist_title)
            else:
                final_filename = Path(output_path).name

            output_path_obj = transcripts_folder() / final_filename
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            save_transcript_file(output_path_obj, content)

            self.status_queue.put(("log", f"Archivo creado: {output_path_obj}"))
            self.status_queue.put(("status", "Proceso terminado."))
            self.status_queue.put(("progress", f"{len(videos)}|{len(videos)}|Completado"))
            self.status_queue.put(("done", f"Las transcripciones se guardaron correctamente en:\n{output_path_obj}"))
        except Exception as exc:  # noqa: BLE001
            self.status_queue.put(("error", str(exc)))

    def _poll_status_queue(self) -> None:
        try:
            while True:
                kind, message = self.status_queue.get_nowait()
                if kind == "log":
                    self.log(message)
                elif kind == "status":
                    self.set_status(message)
                elif kind == "progress":
                    current_str, total_str, title = message.split("|", 2)
                    self.total_videos = int(total_str)
                    self.set_progress(int(current_str), int(total_str), title or None)
                elif kind == "done":
                    self.log(message)
                    self.set_status("Listo.")
                    self.set_progress(self.total_videos or 0, self.total_videos or 0, "Terminado")
                    self.is_running = False
                    self.export_button.configure(state="normal")
                    messagebox.showinfo("Completado", message)
                    # Reset for next playlist
                    self.playlist_url_var.set('')
                    self.output_path_var.set(str(self._default_output_path()))
                elif kind == "error":
                    self.log(f"Error: {message}")
                    self.set_status("Hubo un error.")
                    self.progress_label.configure(text="Progreso: error")
                    self.progress_bar.configure(value=0)
                    self.is_running = False
                    self.export_button.configure(state="normal")
                    messagebox.showerror("Error", message)
        except queue.Empty:
            pass

        self.root.after(100, self._poll_status_queue)


def main() -> None:
    root = Tk()
    app = TranscriptApp(root)
    app.log("Pega una playlist de YouTube y pulsa 'Extraer transcripciones'.")
    root.mainloop()


if __name__ == "__main__":
    main()