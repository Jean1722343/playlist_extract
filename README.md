# 🎬 playlist_extract

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Tkinter-Desktop-4B8BBE?style=for-the-badge" alt="Tkinter" />
  <img src="https://img.shields.io/badge/Flask-Web-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/yt--dlp-Playlist%20reader-F59E0B?style=flat-square" alt="yt-dlp" />
  <img src="https://img.shields.io/badge/youtube--transcript--api-Transcripts-EA4335?style=flat-square" alt="youtube-transcript-api" />
  <img src="https://img.shields.io/badge/Windows-One--click%20launch-0078D6?style=flat-square" alt="Windows" />
</p>

<p align="center">
  App para pegar una playlist de YouTube y exportar todas sus transcripciones en un único archivo de texto, respetando el orden original de la lista.
</p>

---

## Tabla de contenido

- [Vista rápida](#vista-rápida)
- [Qué hace](#qué-hace)
- [Cómo usarlo](#cómo-usarlo)
- [Tecnologías](#tecnologías)
- [Archivos del proyecto](#archivos-del-proyecto)
- [Carpeta de salidas](#carpeta-de-salidas)
- [Entorno `.venv`](#entorno-venv)

---

## Vista rápida

La forma más simple de usarlo es esta:

1. Haz doble clic en [Iniciar_Transcriptor.bat](Iniciar_Transcriptor.bat).
2. Pega la URL de la playlist.
3. Elige dónde guardar el archivo.
4. Pulsa **Extraer transcripciones**.

La primera vez, el lanzador instala automáticamente las dependencias necesarias.

Si prefieres no instalar Python en Windows:

1. Haz doble clic en [Iniciar_Con_Docker.bat](Iniciar_Con_Docker.bat).
2. El navegador se abrirá automáticamente cuando Docker esté listo.
3. Si no se abre solo, entra en `http://localhost:8000`.
4. Pega la playlist y genera el archivo desde el navegador.

La versión web muestra el avance en vivo con barra de progreso, estado y enlace de descarga al terminar.

Docker instala todo automáticamente dentro del contenedor.

---

## Qué hace

El programa automatiza este proceso:

1. Lee la URL de la playlist de YouTube.
2. Obtiene la lista de videos incluidos.
3. Recorre los videos en el mismo orden en que aparecen en la playlist.
4. Busca la transcripción en los idiomas que indiques.
5. Guarda el contenido en un archivo de texto ordenado, legible y fácil de revisar.

Si un video no tiene transcripción, el archivo lo indicará y seguirá con el siguiente.

Mientras se procesa la playlist, verás el porcentaje de avance video por video.

En Docker también verás una barra de progreso en tiempo real mientras la tarea avanza.

---

## Cómo usarlo

### Opción más fácil: doble clic en Windows

Usa [Iniciar_Transcriptor.bat](Iniciar_Transcriptor.bat).

Pasos:

1. Abre el archivo.
2. Se abrirá la ventana del programa.
3. Pega la URL de la playlist.
4. Selecciona el archivo de salida.
5. Pulsa **Extraer transcripciones**.

### Opción sin instalar Python: Docker

Usa [Iniciar_Con_Docker.bat](Iniciar_Con_Docker.bat).

Pasos:

1. Abre el archivo.
2. Espera a que Docker termine de levantar el servicio.
3. Abre `http://localhost:8000`.
4. Pega la playlist.
5. Genera y descarga el archivo.

### Instalación manual

Si prefieres ejecutar desde terminal:

```bash
python app.py
```

El lanzador de Windows y la imagen de Docker instalan las dependencias de forma automática, así que no necesitas un archivo `requirements.txt`.

---

## Tecnologías

| Tecnología | Propósito |
|---|---|
| Python | Lenguaje principal |
| Tkinter | Interfaz de escritorio |
| Flask | Interfaz web para Docker |
| yt-dlp | Leer la playlist y extraer videos |
| youtube-transcript-api | Obtener las transcripciones |
| Docker | Empaquetado y ejecución aislada |

---

## Archivos del proyecto

| Archivo | Descripción |
|---|---|
| `app.py` | Interfaz de escritorio |
| `web_app.py` | Interfaz web para Docker |
| `core.py` | Lógica compartida del proyecto |
| `Dockerfile` | Imagen para ejecutar la app web |
| `docker-compose.yml` | Arranque rápido con Docker |
| `Iniciar_Transcriptor.bat` | Inicio con doble clic en Windows |
| `Iniciar_Con_Docker.bat` | Inicio de la versión Docker |

---

## Carpeta de salidas

Todos los archivos de transcripción se guardan dentro de la carpeta `transcripciones/` del proyecto.

La carpeta se crea sola la primera vez que generas un archivo.

| Carpeta | Uso |
|---|---|
| `transcripciones/` | Guarda únicamente los archivos de transcripción generados |

---

## Resultado generado

El archivo de salida queda con una estructura como esta:

```text
1. Título del video
URL: https://www.youtube.com/watch?v=...
[00:12] Primera frase de la transcripción
[00:18] Siguiente frase
```

En la versión Docker, el nombre del archivo incluye fecha y hora para evitar sobreescrituras.

---

## Requisitos

- Windows, macOS o Linux para la versión Python.
- Docker instalado si quieres usar la versión web.
- Conexión a internet.
- Playlist pública o accesible desde YouTube.

---

## Entorno `.venv`

`.venv` es el entorno virtual de Python del proyecto.

Sirve para:

- aislar dependencias
- evitar conflictos con otros proyectos
- mantener solo las librerías necesarias para esta app

Importante:

- `.venv` no guarda transcripciones
- `.venv` no guarda videos
- el archivo final se guarda donde tú elijas desde la app

---

## Dónde se guarda la información

- La transcripción final se guarda en la carpeta `transcripciones/`.
- La carpeta `transcripciones/` queda en la raíz del proyecto, al lado de `app.py`.
- La URL de la playlist solo se usa para consultar YouTube.
- No se guarda una copia del video dentro de `.venv`.
- En Docker, el archivo se crea dentro de `transcripciones/` y se descarga desde el navegador.

---


## Limitaciones

- Algunas playlists muy grandes pueden tardar un poco.
- Si YouTube cambia su estructura, puede afectar la extracción.
- Si un video no tiene transcripción, no se podrá obtener texto.

---

## Recomendación final

Si quieres la experiencia más simple para cualquier persona, usa [Iniciar_Transcriptor.bat](Iniciar_Transcriptor.bat).

Si quieres evitar instalaciones en tu sistema, usa [Iniciar_Con_Docker.bat](Iniciar_Con_Docker.bat).