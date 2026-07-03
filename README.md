<div align="center">
  <h1>🎬 Streamflix</h1>
  <p><strong>Streaming aggregator desktop app</strong></p>
  <p>9 providers de películas, series, IPTV y TV en vivo — todo en español</p>
</div>

---

## 📸 Capturas

| Provider Screen | Movie Detail | Player |
|---|---|---|
| ![Providers](https://img.shields.io/badge/UI-9%20Providers-red) | ![Detail](https://img.shields.io/badge/UI-Detail%20Page-blue) | ![Player](https://img.shields.io/badge/UI-Player%20with%20Aspect%20Ratio-green) |

---

## 🚀 Descargas

| Plataforma | Archivo | Instalación |
|---|---|---|
| **Linux** (Debian/Ubuntu) | [`streamflix_1.0.0_amd64.deb`](https://github.com/Richiestone18/streamflix-py/releases/latest) | `sudo dpkg -i streamflix_1.0.0_amd64.deb` |
| **Windows** | `Streamflix-Windows-x86_64.exe` | Ejecutar directamente |
| **Linux Portable** | `Streamflix-Linux-x86_64.tar.gz` | Extraer y ejecutar `./Streamflix` |

> **Linux**: requiere GTK 3.24+, WebKit2GTK 4.1, PyGObject (el .deb los instala automáticamente)
> **Windows**: requiere WebView2 Runtime (viene instalado en Windows 10/11 modernos)

---

## 📋 Comandos

```bash
# Abrir app en modo ventana
streamflix

# Abrir en modo fullscreen
streamflix --fullscreen

# Desinstalar
sudo apt remove streamflix
```

---

## 🎮 Controles

| Tecla/Botón | Acción |
|---|---|
| ⛶ (top-bar) | Pantalla completa / Salir |
| ✕ (top-bar / detalle) | Cerrar aplicación |
| **F11** | Toggle fullscreen |
| **ESC** | Cerrar player si está abierto |

### Player

| Control | Descripción |
|---|---|
| **Llenar pantalla** | Video zoom sin barras negras (object-fit: cover) |
| **16:9** | Forzar aspecto 16:9 |
| **4:3** | Forzar aspecto 4:3 |
| **Original** | Aspecto original del video |
| **Fullscreen** | Pantalla completa en el player |

---

## 📡 Providers (9)

| Provider | Tipo | Películas | Series | Servidores |
|---|---|---|---|---|
| **CineCalidad** | Pelis + Series ✅ | ✓ | ✓ | 4 servidores |
| **Pelisplusto** (TioPlus) | Pelis + Series ✅ | ✓ | ✓ | 5 servidores |
| **FlixLatam** | Pelis + Series + Animes ✅ | ✓ | ✓ | 1 servidor |
| **SoloLatino** | Pelis + Series ✅ | ✓ | — | 2 servidores |
| **LatinAnime** | Animes ✅ | — | ✓ | 1 servidor |
| **LaCartoons** | Cartoons (por compañías) ✅ | — | ✓ | 1 servidor (ok.ru) |
| **AnimeFLV** | Animes ⚠️ | — | ✓ | 0 servidores (CF) |
| **IPTV** | ~2240 canales en español | ✓ | ✓ | HLS (.m3u8) |
| **CableVisionHD** | 77 canales en vivo | ✓ | ✓ | iframe |

---

## 💻 Cómo funciona por dentro

### Arquitectura

```
app.py (pywebview desktop app)
  └── inicia uvicorn (FastAPI) en puerto libre
        └── sirve HTML/JS/CSS + API REST
              └── providers scraping con cloudscraper
```

### Estructura del proyecto

```
streamflix-py/
├── app.py                    # Desktop app launcher (pywebview)
├── requirements-app.txt      # Dependencias
├── build_linux.sh            # Build portable Linux
├── build_windows.bat         # Build portable Windows
├── build_deb.sh              # Build .deb package
├── streamflix.spec           # PyInstaller spec
│
├── app/
│   ├── server.py              # FastAPI + HTML UI (TODO el frontend)
│   ├── base.py                # Dataclasses y BaseProvider
│   └── providers/
│       ├── __init__.py        # Registro de providers
│       ├── cinecalidad.py     # CineCalidad (cloudscraper + BS4)
│       ├── pelisplusto.py     # Pelisplusto -> TioPlus.app
│       ├── flixlatam.py       # FlixLatam
│       ├── sololatino.py      # SoloLatino
│       ├── latinanime.py      # LatinAnime
│       ├── lacartoons.py      # LaCartoons (por compañías)
│       ├── animeflv.py        # AnimeFLV (CF protegido)
│       ├── iptv.py            # IPTV (M3U playlists iptv-org)
│       └── cablevisionhd.py   # CableVisionHD (77 canales en vivo)
```

### Backend (FastAPI)

| Endpoint | Qué hace |
|---|---|
| `GET /` | Lista de providers |
| `GET /api/movies/{provider}?page=N` | Películas paginadas (24 por página) |
| `GET /api/tvshows/{provider}?page=N` | Series paginadas |
| `GET /api/genres/{provider}` | Géneros del provider |
| `GET /api/genres/{provider}/{genre_id}?page=N` | Contenido por género |
| `GET /api/search/{provider}?q=query` | Búsqueda |
| `GET /api/servers/{provider}?id=url` | Servidores de un item |
| `GET /api/details/{provider}?id=url` | Detalles de película/serie |

### Frontend (HTML/CSS/JS inline en server.py)

- **Provider Screen**: cards grandes con cada proveedor
- **App Screen**: tabs Películas / Series / Géneros, grid de posters, búsqueda
- **Detail Screen**: poster grande + metadata + botón Ver + temporadas/episodios
- **Player**: iframe o HLS.js para IPTV, selector de aspecto, fullscreen

### Pattern de scraping

Cada provider implementa `BaseProvider` con estos métodos async:

```python
class BaseProvider(ABC):
    name: str                    # Nombre visible
    base_url: str                # URL del sitio
    language: str = "es"

    @abstractmethod
    async def get_movies(self, page: int = 1) -> list[Movie]: ...
    async def get_tv_shows(self, page: int = 1) -> list[TvShow]: ...
    async def search(self, query: str, page: int = 1) -> list: ...
    @abstractmethod
    async def get_genre(self, genre_id: str, page: int = 1) -> list: ...
    @abstractmethod
    async def get_servers(self, movie_id: str) -> list[Server]: ...
    async def get_details(self, item_id: str) -> Optional[MediaDetails]: ...
```

Usan `cloudscraper` para sitios con Cloudflare y `httpx` para sitios directos.

---

## 🔧 Build desde código fuente

```bash
# Clonar
git clone https://github.com/Richiestone18/streamflix-py.git
cd streamflix-py

# Crear venv e instalar
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-app.txt

# Ejecutar en modo dev (navegador)
uvicorn app.server:app --host 0.0.0.0 --port 8080
# Abrir: http://localhost:8080/browse

# Ejecutar como desktop app
python3 app.py

# Build portable
./build_linux.sh         # Linux single binary
# o en Windows:
build_windows.bat       # Windows .exe

# Build .deb
./build_deb.sh          # Linux .deb package
```

---

## 📦 Dependencias

### Python
- `fastapi`, `uvicorn` — servidor web
- `httpx`, `cloudscraper` — HTTP con soporte Cloudflare
- `beautifulsoup4`, `lxml` — parsing HTML
- `pywebview` — ventana nativa de escritorio
- `pyinstaller` — build de ejecutable

### Sistema (Linux)
- `libgtk-3-0` — GTK 3
- `libwebkit2gtk-4.1-0` — WebKit2GTK
- `gir1.2-webkit2-4.1` — GObject Introspection para WebKit
- `python3-gi` — PyGObject

---

## ⚠️ Providers rotos

- **PoseidonHD**: todos los dominios están parked o redirigen
- **Cine24h**: Cloudflare bloquea todas las peticiones

---

## 📝 Licencia

MIT