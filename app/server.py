"""FastAPI server for streamflix-py."""
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from .providers import PROVIDERS, get_provider
from dataclasses import asdict

app = FastAPI(title="Streamflix API")


def serialize(obj):
    """Convert dataclass to dict for JSON response."""
    if hasattr(obj, '__dataclass_fields__'):
        return {k: serialize(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [serialize(i) for i in obj]
    return obj


@app.get("/")
async def root():
    return {"message": "Streamflix API", "providers": [p.name for p in PROVIDERS]}


@app.get("/api/providers")
async def list_providers():
    results = []
    # Providers whose items are direct live streams (skip detail screen)
    IPTV_PROVIDERS = {
        "IPTV", "CableVisionHD", "MAGISTV",
        "PlutoTV MX", "PlutoTV AR",
        "TvporinternetHD", "TvLibrefutbol",
    }
    for p in PROVIDERS:
        results.append({
            "name": p.name,
            "base_url": p.base_url,
            "language": p.language,
            "is_iptv": p.name in IPTV_PROVIDERS,
        })
    return {"providers": results}


@app.get("/api/tvshows/{provider_name}")
async def get_tv_shows(provider_name: str, page: int = Query(1, ge=1)):
    p = get_provider(provider_name)
    if not p:
        return {"error": f"Provider '{provider_name}' not found"}
    shows = await p.get_tv_shows(page) if hasattr(p, 'get_tv_shows') else []
    return {"provider": provider_name, "page": page, "results": [
        {"id": s.id, "title": s.title, "poster": s.poster}
        for s in shows
    ]}


@app.get("/api/movies/{provider_name}")
async def get_movies(provider_name: str, page: int = Query(1, ge=1)):
    p = get_provider(provider_name)
    if not p:
        return {"error": f"Provider '{provider_name}' not found"}
    movies = await p.get_movies(page)
    return {"provider": provider_name, "page": page, "results": [
        {"id": m.id, "title": m.title, "poster": m.poster, "year": m.year}
        for m in movies
    ]}


@app.get("/api/servers/{provider_name}")
async def get_servers(provider_name: str, id: str = Query(...)):
    p = get_provider(provider_name)
    if not p:
        return {"error": f"Provider '{provider_name}' not found"}
    servers = await p.get_servers(id)
    return {"provider": provider_name, "results": [
        {"name": s.name, "url": s.id} for s in servers
    ]}


@app.get("/api/search/{provider_name}")
async def search(provider_name: str, q: str = Query(""), page: int = Query(1, ge=1)):
    p = get_provider(provider_name)
    if not p:
        return {"error": f"Provider '{provider_name}' not found"}
    results = await p.search(q, page)
    return {"provider": provider_name, "query": q, "results": [
        {"id": item.id, "title": item.title, "poster": getattr(item, "poster", None),
         "type": type(item).__name__}
        if not isinstance(item, dict) else item
        for item in results
    ]}


@app.get("/api/genre/{provider_name}")
async def get_genre(provider_name: str, id: str = Query(...), page: int = Query(1, ge=1)):
    p = get_provider(provider_name)
    if not p:
        return {"error": f"Provider '{provider_name}' not found"}
    results = await p.get_genre(id, page)
    return {"provider": provider_name, "genre": id, "results": [
        {"id": m.id, "title": m.title, "poster": m.poster, "year": m.year}
        for m in results
    ]}


@app.get("/api/details/{provider_name}")
async def get_details(provider_name: str, id: str = Query(...)):
    """Get detailed info about a movie or series."""
    p = get_provider(provider_name)
    if not p:
        return {"error": f"Provider '{provider_name}' not found"}
    details = await p.get_details(id)
    if not details:
        return {"error": "Could not fetch details"}
    return {"provider": provider_name, "details": serialize(details)}


@app.get("/browse", response_class=HTMLResponse)
async def browse():
    return BROWSE_HTML


BROWSE_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Streamflix</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0a12;--card:#1a1a2e;--card-hover:#222240;--accent:#e94560;--accent2:#0f3460;--text:#eee;--text-dim:#888;--radius:12px}
body{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden}
::-webkit-scrollbar{width:8px}::-webkit-scrollbar-track{background:var(--bg)}::-webkit-scrollbar-thumb{background:var(--accent2);border-radius:4px}

/* PROVIDER SELECT SCREEN */
#provider-screen{padding:2rem;min-height:100vh;display:flex;flex-direction:column;align-items:center}
#provider-screen h1{font-size:2.5rem;margin-bottom:.5rem;color:var(--accent)}
#provider-screen .subtitle{color:var(--text-dim);margin-bottom:3rem;font-size:1.1rem}
.provider-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1.5rem;max-width:1100px;width:100%}
.provider-card{background:var(--card);border-radius:var(--radius);padding:2rem 1.5rem;cursor:pointer;transition:all .25s;text-align:center;border:2px solid transparent}
.provider-card:hover{background:var(--card-hover);border-color:var(--accent);transform:translateY(-4px);box-shadow:0 8px 24px rgba(233,69,96,.2)}
.provider-card .icon{font-size:3rem;margin-bottom:1rem}
.provider-card .name{font-size:1.4rem;font-weight:700;margin-bottom:.3rem}
.provider-card .desc{color:var(--text-dim);font-size:.85rem}
.provider-card .count{margin-top:.5rem;font-size:.8rem;color:var(--accent)}

/* MAIN APP */
#app-screen{display:none;min-height:100vh}
.top-bar{background:var(--card);padding:.8rem 2rem;display:flex;align-items:center;gap:1rem;position:sticky;top:0;z-index:50}
.top-bar .logo{color:var(--accent);font-size:1.4rem;font-weight:700;cursor:pointer;white-space:nowrap}
.top-bar .back-btn{background:var(--accent2);color:var(--text);border:0;padding:.5rem 1rem;border-radius:8px;cursor:pointer;font-size:.9rem}
.top-bar .back-btn:hover{background:var(--accent)}
.top-bar .top-btn{background:transparent;color:var(--text);border:1px solid var(--accent2);padding:.5rem .8rem;border-radius:8px;cursor:pointer;font-size:1rem;line-height:1}
.top-bar .top-btn:hover{background:var(--accent2)}
.search-box{flex:1;display:flex;gap:.5rem;max-width:400px;margin-left:auto}
.search-box input{flex:1;background:var(--bg);border:1px solid var(--accent2);color:var(--text);padding:.6rem 1rem;border-radius:8px;outline:0;font-size:.95rem}
.search-box input:focus{border-color:var(--accent)}
.search-box button{background:var(--accent);color:#fff;border:0;padding:.6rem 1.2rem;border-radius:8px;cursor:pointer;font-weight:600}

/* TABS */
.tabs{display:flex;gap:0;padding:0 2rem;background:var(--card);border-bottom:1px solid var(--accent2)}
.tab{padding:.8rem 1.5rem;cursor:pointer;color:var(--text-dim);border-bottom:3px solid transparent;transition:all .2s;font-weight:500}
.tab:hover{color:var(--text)}
.tab.active{color:var(--accent);border-bottom-color:var(--accent)}

/* GENRES BAR */
#genres-bar{display:none;flex-wrap:wrap;gap:.5rem;padding:1rem 2rem;background:var(--bg);border-bottom:1px solid var(--accent2)}
#genres-bar.show{display:flex}
#genres-bar button{background:var(--accent2);color:var(--text);border:0;padding:.4rem .9rem;border-radius:6px;cursor:pointer;font-size:.85rem;transition:all .2s}
#genres-bar button:hover{background:var(--accent)}
#genres-bar button.active{background:var(--accent)}

/* CONTENT GRID */
.content-area{padding:1.5rem 2rem;min-height:400px}
.content-area h2{margin-bottom:1rem;font-size:1.3rem;color:var(--text)}
.movie-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:1.2rem}
.movie-card{background:var(--card);border-radius:var(--radius);overflow:hidden;cursor:pointer;transition:all .25s;position:relative}
.movie-card:hover{transform:scale(1.05);box-shadow:0 6px 20px rgba(0,0,0,.4)}
.movie-card img{width:100%;aspect-ratio:2/3;object-fit:cover;display:block;background:var(--accent2)}
.movie-card .title{padding:.6rem;font-size:.85rem;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.movie-card .badge{position:absolute;top:.4rem;right:.4rem;background:var(--accent);color:#fff;font-size:.7rem;padding:.15rem .4rem;border-radius:4px;font-weight:600}

/* LOAD MORE */
#load-more{display:none;margin:2rem auto;padding:.8rem 2.5rem;background:var(--accent);color:#fff;border:0;border-radius:var(--radius);cursor:pointer;font-size:1rem;font-weight:600}
#load-more.show{display:block}
#load-more:hover{background:#d63851}
#load-more:disabled{background:#555;cursor:default}

/* DETAIL SCREEN */
#detail-screen{display:none;min-height:100vh;animation:fadeIn .3s}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.detail-backdrop{position:relative;height:340px;background-size:cover;background-position:center}
.detail-backdrop::after{content:'';position:absolute;inset:0;background:linear-gradient(to bottom,rgba(10,10,18,.3),var(--bg))}
.detail-back{position:absolute;top:1rem;left:1rem;z-index:10;background:rgba(0,0,0,.7);color:#fff;border:0;padding:.6rem 1rem;border-radius:8px;cursor:pointer;font-size:.9rem}
.detail-back:hover{background:var(--accent)}
.detail-content{display:flex;gap:2rem;padding:0 2rem;max-width:1000px;margin:-120px auto 0;position:relative;z-index:5}
.detail-poster{width:240px;flex-shrink:0;border-radius:var(--radius);overflow:hidden;box-shadow:0 8px 30px rgba(0,0,0,.5)}
.detail-poster img{width:100%;display:block}
.detail-info{flex:1;padding-top:1rem}
.detail-info h1{font-size:2rem;margin-bottom:.5rem}
.detail-meta{display:flex;flex-wrap:wrap;gap:.8rem;margin-bottom:1rem;color:var(--text-dim);font-size:.9rem}
.detail-meta span{display:flex;align-items:center;gap:.3rem}
.detail-meta .rating{color:#ffd700;font-weight:600}
.detail-genres{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1rem}
.detail-genres span{background:var(--accent2);padding:.3rem .7rem;border-radius:6px;font-size:.8rem}
.detail-overview{line-height:1.7;color:#ccc;margin-bottom:1rem}
.detail-cast{font-size:.85rem;color:var(--text-dim);margin-bottom:.5rem}
.detail-cast b{color:var(--text)}
.play-btn{background:var(--accent);color:#fff;border:0;padding:.8rem 2.5rem;border-radius:var(--radius);cursor:pointer;font-size:1.1rem;font-weight:700;margin:.5rem 0;transition:all .2s}
.play-btn:hover{background:#d63851;transform:scale(1.03)}
.play-btn:disabled{background:#555;cursor:default;transform:none}

/* SEASONS */
.seasons-section{padding:2rem;max-width:1000px;margin:0 auto}
.seasons-section h2{font-size:1.4rem;margin-bottom:1rem}
.season-tabs{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1.5rem}
.season-tab{background:var(--accent2);color:var(--text);border:0;padding:.5rem 1.2rem;border-radius:8px;cursor:pointer;font-size:.95rem;transition:all .2s}
.season-tab:hover{background:var(--accent2);opacity:.8}
.season-tab.active{background:var(--accent)}
.episodes-list{display:flex;flex-direction:column;gap:.5rem}
.episode-item{background:var(--card);border-radius:8px;padding:.8rem 1.2rem;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:1rem}
.episode-item:hover{background:var(--card-hover);border-left:3px solid var(--accent)}
.episode-number{font-size:1.5rem;font-weight:700;color:var(--accent);min-width:40px;text-align:center}
.episode-title{flex:1}
.episode-title .ep-name{font-size:1rem}
.episode-title .ep-num{font-size:.8rem;color:var(--text-dim)}
.episode-play{background:var(--accent);color:#fff;border:0;padding:.4rem 1rem;border-radius:6px;cursor:pointer;font-size:.85rem}
.episode-play:hover{background:#d63851}

/* PLAYER */
#player-overlay{display:none;position:fixed;inset:0;background:#000;z-index:100;flex-direction:column}
#player-overlay.active{display:flex}
.player-top{display:flex;justify-content:space-between;align-items:center;padding:.5rem 1rem;background:#111}
.player-top .info{display:flex;align-items:center;gap:.5rem;color:#fff;font-size:.95rem}
.player-top button{background:0;border:0;color:#fff;font-size:1.2rem;cursor:pointer;padding:.4rem .8rem}
.player-top button:hover{color:var(--accent)}
.server-list{display:flex;gap:.4rem;flex-wrap:wrap;padding:.5rem 1rem;background:#0a0a12}
.server-list button{background:var(--accent2);color:var(--text);border:0;padding:.4rem .8rem;border-radius:6px;cursor:pointer;font-size:.85rem}
.server-list button:hover,.server-list button.active{background:var(--accent)}
#player-frame{flex:1;border:0;width:100%}

/* UTILS */
.loading{text-align:center;padding:3rem;color:var(--text-dim)}
.no-results{text-align:center;padding:3rem;color:var(--text-dim);grid-column:1/-1}
.error-msg{color:var(--accent);text-align:center;padding:2rem}
</style>
</head>
<body>

<!-- PROVIDER SELECT SCREEN -->
<div id="provider-screen">
  <h1>🎬 Streamflix</h1>
  <p class="subtitle">Selecciona un proveedor para comenzar</p>
  <div class="provider-grid" id="provider-grid"></div>
</div>

<!-- MAIN APP SCREEN -->
<div id="app-screen">
  <div class="top-bar">
    <button class="back-btn" onclick="showProviders()">← Proveedores</button>
    <span class="logo" onclick="showProviders()">🎬 Streamflix</span>
    <div class="search-box">
      <input id="search-input" placeholder="Buscar..." onkeydown="if(event.key==='Enter')doSearch()">
      <button onclick="doSearch()">🔍</button>
    </div>
    <button onclick="toggleAppFullscreen()" id="fullscreen-btn" class="top-btn" title="Pantalla completa">⛶</button>
    <button onclick="closeApp()" id="close-btn" class="top-btn" title="Cerrar">✕</button>
  </div>
  <div class="tabs">
    <div class="tab active" data-tab="movies" onclick="switchTab('movies')">🎬 Películas</div>
    <div class="tab" data-tab="series" onclick="switchTab('series')">📺 Series</div>
    <div class="tab" data-tab="genres" onclick="switchTab('genres')">🎭 Géneros</div>
  </div>
  <div id="genres-bar"></div>
  <div class="content-area" id="content-area">
    <div class="loading">Cargando...</div>
  </div>
  <button id="load-more" onclick="loadMore()">Cargar más</button>
</div>

<!-- DETAIL SCREEN -->
<div id="detail-screen">
  <div id="detail-backdrop" class="detail-backdrop">
    <button class="detail-back" onclick="closeDetail()">← Volver</button>
    <button class="detail-close" onclick="closeApp()" title="Cerrar">✕</button>
  </div>
  <div class="detail-content" id="detail-content"></div>
  <div class="seasons-section" id="seasons-section"></div>
</div>

<!-- PLAYER -->
<div id="player-overlay">
  <div class="player-top">
    <span class="info" id="player-title"></span>
    <div class="player-controls">
      <select id="aspect-select" onchange="setAspect(this.value)" style="background:#222;color:#fff;border:1px solid #444;padding:3px 6px;border-radius:4px;cursor:pointer">
        <option value="fill">Llenar pantalla</option>
        <option value="16:9">16:9</option>
        <option value="4:3">4:3</option>
        <option value="original">Original</option>
      </select>
      <button onclick="togglePlayerFullscreen()" title="Pantalla completa">⛶</button>
      <button onclick="closePlayer()">✕ Cerrar</button>
    </div>
  </div>
  <div class="server-list" id="server-buttons"></div>
  <div id="player-container" style="flex:1;display:flex;align-items:center;justify-content:center;background:#000;overflow:hidden">
    <div id="player-video-wrapper" style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;overflow:hidden">
      <iframe id="player-frame" allowfullscreen allow="autoplay; encrypted-media" style="border:0;width:100%;height:100%"></iframe>
      <video id="player-video" controls autoplay style="display:none" allowfullscreen></video>
    </div>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<script>
// Fallback: si HLS.js no carga del CDN, cargarlo de otro source
if (typeof Hls === 'undefined') {
  var s = document.createElement('script');
  s.src = 'https://unpkg.com/hls.js@latest';
  document.head.appendChild(s);
}
</script>

<script>
let currentProvider = '';
let currentTab = 'movies';
let currentPage = 1;
let currentMode = 'movies'; // 'movies' | 'series' | 'genre' | 'search'
let currentGenreId = '';
let currentSearchQ = '';
let isLoading = false;
let currentDetailItem = null;
let isIptvProvider = false; // IPTV providers skip detail screen, play directly

// ===== PROVIDER SCREEN =====
async function loadProviders() {
  const r = await fetch('/api/providers');
  const d = await r.json();
  const grid = document.getElementById('provider-grid');
  const icons = {CineCalidad:'🎥', Pelisplusto:'🍿', FlixLatam:'🎬', SoloLatino:'📺', LatinAnime:'斓', LaCartoons:'🎨', AnimeFLV:'🍁', JKanime:'Anime', IPTV:'📡', CableVisionHD:'📺', Doramasflix:'🎭', PelisflixHD:'🍿', MAGISTV:'📡', SeriesFlix:'📺', TvporinternetHD:'📡', TvLibrefutbol:'⚽', 'PlutoTV MX':'🇲🇽', 'PlutoTV AR':'🇦🇷', Animefenix:'🔥', Latanime:'🅰️'};
  grid.innerHTML = d.providers.map(p => `
    <div class="provider-card" onclick="selectProvider('${p.name}', ${p.is_iptv})">
      <div class="icon">${icons[p.name]||'🎬'}</div>
      <div class="name">${p.name}</div>
      <div class="desc">${p.language === 'es' ? 'Español' : p.language}</div>
      <div class="count" id="count-${p.name}"></div>
    </div>
  `).join('');
  // Load movie counts in background
  for (const p of d.providers) {
    fetch(`/api/movies/${p.name}?page=1`).then(r=>r.json()).then(d=>{
      const el = document.getElementById('count-'+p.name);
      if (el) el.textContent = `${d.results.length}+ títulos`;
    }).catch(()=>{});
  }
}

function selectProvider(name, isIptv) {
  currentProvider = name;
  isIptvProvider = !!isIptv;
  document.getElementById('provider-screen').style.display = 'none';
  document.getElementById('app-screen').style.display = 'block';
  // Auto-detect: try movies first; if empty, switch to series
  loadMovies(1).then(d => {
    if (!d.results || d.results.length === 0) {
      switchTab('series');
    }
  });
}

function showProviders() {
  document.getElementById('provider-screen').style.display = 'flex';
  document.getElementById('app-screen').style.display = 'none';
  document.getElementById('detail-screen').style.display = 'none';
  document.getElementById('player-overlay').classList.remove('active');
  document.getElementById('player-frame').src = '';
}

// ===== TABS =====
function switchTab(tab) {
  currentTab = tab;
  currentMode = tab === 'series' ? 'series' : (tab === 'movies' ? 'movies' : currentMode);
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  document.getElementById('genres-bar').classList.toggle('show', tab === 'genres');
  document.getElementById('search-input').value = '';
  
  if (tab === 'genres') {
    loadGenres();
  } else if (tab === 'movies') {
    loadMovies(1);
  } else if (tab === 'series') {
    loadSeries(1);
  }
}

// ===== GENRES =====
async function loadGenres() {
  document.getElementById('content-area').innerHTML = '<div class="loading">Cargando géneros...</div>';
  document.getElementById('load-more').classList.remove('show');
  const r = await fetch(`/api/search/${currentProvider}?q=`);
  const d = await r.json();
  const genres = d.results.filter(i => i.type === 'genre');
  const bar = document.getElementById('genres-bar');
  bar.innerHTML = genres.map(g => `<button onclick="loadGenre('${g.id}')">${g.name}</button>`).join('');
  bar.classList.add('show');
  if (genres.length > 0) {
    loadGenre(genres[0].id);
  } else {
    document.getElementById('content-area').innerHTML = '<div class="no-results">No hay géneros disponibles</div>';
  }
}

async function loadGenre(genreId) {
  currentGenreId = genreId;
  currentMode = 'genre';
  currentPage = 1;
  document.getElementById('content-area').innerHTML = '<div class="loading">Cargando...</div>';
  document.getElementById('load-more').classList.remove('show');
  document.querySelectorAll('#genres-bar button').forEach(b => b.classList.toggle('active', b.textContent === genreId));
  const r = await fetch(`/api/genre/${currentProvider}?id=${encodeURIComponent(genreId)}&page=1`);
  const d = await r.json();
  renderGrid(d.results);
  if (d.results.length > 0) currentPage = 2;
}

// ===== MOVIES =====
async function loadMovies(page) {
  currentMode = 'movies';
  currentPage = page;
  document.getElementById('content-area').innerHTML = '<div class="loading">Cargando películas...</div>';
  document.getElementById('load-more').classList.remove('show');
  const r = await fetch(`/api/movies/${currentProvider}?page=${page}`);
  const d = await r.json();
  renderGrid(d.results);
  if (d.results.length > 0) currentPage = page + 1;
  return d;
}

// ===== SERIES =====
async function loadSeries(page) {
  currentMode = 'series';
  currentPage = page;
  document.getElementById('content-area').innerHTML = '<div class="loading">Cargando series...</div>';
  document.getElementById('load-more').classList.remove('show');
  const r = await fetch(`/api/tvshows/${currentProvider}?page=${page}`);
  const d = await r.json();
  renderGrid(d.results);
  if (d.results.length > 0) currentPage = page + 1;
}

// ===== SEARCH =====
async function doSearch() {
  const q = document.getElementById('search-input').value.trim();
  if (!q) { switchTab(currentTab); return; }
  currentMode = 'search';
  currentSearchQ = q;
  currentPage = 1;
  document.getElementById('content-area').innerHTML = '<div class="loading">Buscando...</div>';
  document.getElementById('load-more').classList.remove('show');
  const r = await fetch(`/api/search/${currentProvider}?q=${encodeURIComponent(q)}&page=1`);
  const d = await r.json();
  const items = d.results.filter(i => i.type !== 'genre');
  renderGrid(items);
  if (items.length > 0) currentPage = 2;
}

// ===== RENDER GRID =====
function renderGrid(items) {
  const area = document.getElementById('content-area');
  if (!items || !items.length) {
    area.innerHTML = '<div class="no-results">Sin resultados</div>';
    return;
  }
  area.innerHTML = '<div class="movie-grid"></div>';
  const grid = area.querySelector('.movie-grid');
  for (const m of items) {
    if (m.type === 'genre') continue;
    const card = document.createElement('div');
    card.className = 'movie-card';
    const isSeries = currentMode === 'series';
    card.innerHTML = `
      <img src="${m.poster||''}" alt="${m.title}" loading="lazy" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22300%22><rect fill=%22%231a1a2e%22 width=%22200%22 height=%22300%22/><text x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 fill=%22%23888%22 font-size=%2214%22>${(m.title||'').replace(/'/g,'').substring(0,20)}</text></svg>'">
      ${isSeries?'<div class="badge">Serie</div>':''}
      <div class="title">${m.title}</div>
    `;
    card.onclick = () => {
      if (isIptvProvider) {
        playIptvChannel(m.id, m.title);
      } else {
        openDetail(m.id, isSeries || currentMode === 'series');
      }
    };
    grid.appendChild(card);
  }
  const btn = document.getElementById('load-more');
  btn.textContent = `Cargar más (página ${currentPage})`;
  btn.disabled = false;
  btn.classList.add('show');
}

// ===== LOAD MORE =====
async function loadMore() {
  if (isLoading) return;
  isLoading = true;
  const btn = document.getElementById('load-more');
  btn.textContent = 'Cargando...';
  btn.disabled = true;
  let url;
  if (currentMode === 'genre')
    url = `/api/genre/${currentProvider}?id=${encodeURIComponent(currentGenreId)}&page=${currentPage}`;
  else if (currentMode === 'search')
    url = `/api/search/${currentProvider}?q=${encodeURIComponent(currentSearchQ)}&page=${currentPage}`;
  else if (currentMode === 'series')
    url = `/api/tvshows/${currentProvider}?page=${currentPage}`;
  else
    url = `/api/movies/${currentProvider}?page=${currentPage}`;
  const r = await fetch(url);
  const d = await r.json();
  if (!d.results || !d.results.length) {
    btn.textContent = 'No hay más resultados';
    btn.disabled = true;
    isLoading = false;
    return;
  }
  const grid = document.querySelector('.movie-grid');
  if (grid) {
    for (const m of d.results) {
      if (m.type === 'genre') continue;
      const card = document.createElement('div');
      card.className = 'movie-card';
      const isSeries = currentMode === 'series';
      card.innerHTML = `
        <img src="${m.poster||''}" alt="${m.title}" loading="lazy" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22300%22><rect fill=%22%231a1a2e%22 width=%22200%22 height=%22300%22/><text x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 fill=%22%23888%22 font-size=%2214%22>${(m.title||'').replace(/'/g,'').substring(0,20)}</text></svg>'">
        ${isSeries?'<div class="badge">Serie</div>':''}
        <div class="title">${m.title}</div>
      `;
      card.onclick = () => {
        if (isIptvProvider) {
          playIptvChannel(m.id, m.title);
        } else {
          openDetail(m.id, isSeries);
        }
      };
      grid.appendChild(card);
    }
  }
  currentPage++;
  btn.textContent = `Cargar más (página ${currentPage})`;
  btn.disabled = false;
  isLoading = false;
}

// ===== DETAIL SCREEN =====
async function openDetail(itemId, isSeries) {
  document.getElementById('app-screen').style.display = 'none';
  document.getElementById('detail-screen').style.display = 'block';
  document.getElementById('detail-content').innerHTML = '<div class="loading">Cargando información...</div>';
  document.getElementById('seasons-section').innerHTML = '';
  window.scrollTo(0, 0);
  
  const r = await fetch(`/api/details/${currentProvider}?id=${encodeURIComponent(itemId)}`);
  const d = await r.json();
  if (d.error) {
    document.getElementById('detail-content').innerHTML = `<div class="error-msg">${d.error}</div>`;
    return;
  }
  const det = d.details;
  currentDetailItem = det;
  
  // Backdrop
  const backdrop = document.getElementById('detail-backdrop');
  if (det.banner) {
    backdrop.style.backgroundImage = `url("${det.banner}")`;
  } else if (det.poster) {
    backdrop.style.backgroundImage = `url("${det.poster}")`;
  } else {
    backdrop.style.background = 'var(--card)';
  }
  
  // Content
  let html = `
    <div class="detail-poster">
      <img src="${det.poster||det.banner||''}" alt="${det.title}" onerror="this.style.display='none'">
    </div>
    <div class="detail-info">
      <h1>${det.title}</h1>
      <div class="detail-meta">
        ${det.year ? `<span>📅 ${det.year}</span>` : ''}
        ${det.rating ? `<span class="rating">⭐ ${det.rating}/10</span>` : ''}
        ${det.quality ? `<span>🎞️ ${det.quality}</span>` : ''}
        ${det.audio ? `<span>🔊 ${det.audio}</span>` : ''}
        ${det.type === 'series' ? `<span>📺 Serie</span>` : `<span>🎬 Película</span>`}
      </div>
      ${det.genres && det.genres.length ? `<div class="detail-genres">${det.genres.map(g=>`<span>${g}</span>`).join('')}</div>` : ''}
      ${det.overview ? `<div class="detail-overview">${det.overview}</div>` : ''}
      ${det.directors && det.directors.length ? `<div class="detail-cast"><b>Director:</b> ${det.directors.join(', ')}</div>` : ''}
      ${det.cast && det.cast.length ? `<div class="detail-cast"><b>Reparto:</b> ${det.cast.slice(0,8).join(', ')}${det.cast.length>8?'...':''}</div>` : ''}
      <button class="play-btn" onclick="playItem('${det.id.replace(/'/g,'')}', ${det.type==='series'})">▶ Ver ${det.type==='series'?'serie':'película'}</button>
    </div>
  `;
  document.getElementById('detail-content').innerHTML = html;
  
  // Seasons (series only)
  if (det.type === 'series' && det.seasons && det.seasons.length > 0) {
    renderSeasons(det.seasons, det.id);
  }
}

function renderSeasons(seasons, seriesId) {
  const section = document.getElementById('seasons-section');
  let html = '<h2>Temporadas</h2><div class="season-tabs">';
  seasons.forEach((s, i) => {
    html += `<button class="season-tab ${i===0?'active':''}" onclick="showSeason(${i})">Temporada ${s.number}</button>`;
  });
  html += '</div><div id="episodes-container"></div>';
  section.innerHTML = html;
  // Store seasons globally
  window._seasons = seasons;
  window._seriesId = seriesId;
  showSeason(0);
}

function showSeason(idx) {
  document.querySelectorAll('.season-tab').forEach((t,i) => t.classList.toggle('active', i === idx));
  const s = window._seasons[idx];
  if (!s) return;
  const container = document.getElementById('episodes-container');
  container.innerHTML = '<div class="episodes-list">' + s.episodes.map(e => `
    <div class="episode-item" onclick="playEpisode('${e.id.replace(/'/g,'')}')">
      <div class="episode-number">${e.number}</div>
      <div class="episode-title">
        <div class="ep-name">${e.title}</div>
        <div class="ep-num">T${s.number} E${e.number}</div>
      </div>
      <button class="episode-play" onclick="event.stopPropagation(); playEpisode('${e.id.replace(/'/g,'')}')">▶</button>
    </div>
  `).join('') + '</div>';
}

function closeDetail() {
  document.getElementById('detail-screen').style.display = 'none';
  document.getElementById('app-screen').style.display = 'block';
}

// ===== PLAYER =====
async function playIptvChannel(itemId, title) {
  // IPTV channels go directly to the player, no detail screen
  document.getElementById('player-title').textContent = title || 'Canal en Vivo';
  const sb = document.getElementById('server-buttons');
  sb.innerHTML = '<div style="padding:.5rem 1rem;color:#888;width:100%;text-align:center">Conectando...</div>';
  document.getElementById('player-overlay').classList.add('active');

  const r = await fetch(`/api/servers/${currentProvider}?id=${encodeURIComponent(itemId)}`);
  const d = await r.json();
  if (!d.results || !d.results.length) {
    sb.innerHTML = '<div style="padding:.5rem 1rem;color:var(--accent);width:100%;text-align:center">Sin servidores disponibles</div>';
    return;
  }
  const sb2 = document.getElementById('server-buttons');
  sb2.innerHTML = d.results.map((s,i) => `<button class="${i===0?'active':''}" onclick="playServer(${i})">${s.name}</button>`).join('');
  window._servers = d.results;
  playUrl(d.results[0].url);
}

async function playItem(itemId, isSeries) {
  if (isSeries && window._seasons && window._seasons.length > 0) {
    // Play first episode of first season
    const firstEp = window._seasons[0].episodes[0];
    if (firstEp) {
      playEpisode(firstEp.id);
      return;
    }
  }
  await loadServersAndPlay(itemId);
}

async function playEpisode(epId) {
  await loadServersAndPlay(epId);
}

async function loadServersAndPlay(itemId) {
  const r = await fetch(`/api/servers/${currentProvider}?id=${encodeURIComponent(itemId)}`);
  const d = await r.json();
  if (!d.results || !d.results.length) {
    alert('Sin servidores disponibles');
    return;
  }
  const sb = document.getElementById('server-buttons');
  sb.innerHTML = d.results.map((s,i) => `<button class="${i===0?'active':''}" onclick="playServer(${i})">${s.name}</button>`).join('');
  window._servers = d.results;
  document.getElementById('player-title').textContent = d.results[0].name;
  playUrl(d.results[0].url);
  document.getElementById('player-overlay').classList.add('active');
}

function playServer(idx) {
  if (!window._servers || !window._servers[idx]) return;
  document.querySelectorAll('.server-list button').forEach((b,i) => b.classList.toggle('active', i === idx));
  const url = window._servers[idx].url;
  document.getElementById('player-title').textContent = window._servers[idx].name;
  playUrl(url);
}

let currentAspect = 'fill';

function setAspect(ratio) {
  currentAspect = ratio;
  const wrapper = document.getElementById('player-video-wrapper');
  const iframe = document.getElementById('player-frame');
  const video = document.getElementById('player-video');
  
  function apply(el) {
    if (!el || !el.style.display || el.style.display === 'none') return;
    el.style.objectFit = 'contain';
    el.style.width = '100%';
    el.style.height = '100%';
    
    if (ratio === 'fill') {
      el.style.objectFit = 'cover';
    } else if (ratio === '16:9') {
      el.style.width = '100%';
      el.style.aspectRatio = '16/9';
      el.style.maxHeight = '100%';
    } else if (ratio === '4:3') {
      el.style.width = '100%';
      el.style.aspectRatio = '4/3';
      el.style.maxHeight = '100%';
    } else {
      // original - contain
      el.style.objectFit = 'contain';
    }
  }
  
  apply(iframe);
  apply(video);
}

function toggleFullscreen() {
  const overlay = document.getElementById('player-overlay');
  if (!document.fullscreenElement) {
    overlay.requestFullscreen().catch(() => {
      // Fallback: try fullscreen on player-video or player-frame
      const video = document.getElementById('player-video');
      if (video.style.display !== 'none') {
        video.requestFullscreen().catch(()=>{});
      } else {
        document.getElementById('player-frame').requestFullscreen().catch(()=>{});
      }
    });
  } else {
    document.exitFullscreen();
  }
}

function playUrl(url) {
  const iframe = document.getElementById('player-frame');
  const video = document.getElementById('player-video');
  // Destroy previous HLS instance
  if (window._hls) { window._hls.destroy(); window._hls = null; }
  
  const isHls = url.endsWith('.m3u8') || url.includes('.m3u8');
  
  if (isHls) {
    if (window.Hls && Hls.isSupported()) {
      // HLS stream - use video tag with hls.js
      iframe.style.display = 'none';
      video.style.display = 'block';
      const hls = new Hls();
      hls.loadSource(url);
      hls.attachMedia(video);
      window._hls = hls;
      hls.on(Hls.Events.MANIFEST_PARSED, () => video.play().catch(()=>{}));
      hls.on(Hls.Events.ERROR, (e, data) => {
        if (data.fatal) {
          // Fallback: embed player in iframe
          embedHlsPlayer(url);
        }
      });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      // Safari nativo
      iframe.style.display = 'none';
      video.style.display = 'block';
      video.src = url;
      video.play().catch(()=>{});
    } else {
      // Sin HLS.js: embeber player en iframe
      embedHlsPlayer(url);
    }
  } else {
    // Regular URL - use iframe
    iframe.style.display = 'block';
    video.style.display = 'none';
    video.pause();
    iframe.src = url;
  }
  
  // Apply current aspect ratio
  setAspect(currentAspect);
}

function embedHlsPlayer(url) {
  const iframe = document.getElementById('player-frame');
  const video = document.getElementById('player-video');
  video.pause();
  video.style.display = 'none';
  iframe.style.display = 'block';
  // Player HTML embebido que carga HLS.js desde CDN
  const html = '<!DOCTYPE html>\n' +
    '<html><head><meta charset="UTF-8">\n' +
    '<style>*{margin:0;padding:0;box-sizing:border-box}body{background:#000}video{width:100%;height:100%}</style>\n' +
    '<scr' + 'ipt src="https://cdn.jsdelivr.net/npm/hls.js@latest"></scr' + 'ipt>\n' +
    '<scr' + 'ipt src="https://unpkg.com/hls.js@latest"></scr' + 'ipt>\n' +
    '</head><body>\n' +
    '<video id="v" controls autoplay playsinline style="width:100%;height:100%;object-fit:contain"></video>\n' +
    '<scr' + 'ipt>\n' +
    'var v=document.getElementById("v");\n' +
    'if(typeof Hls!=="undefined"&&Hls.isSupported()){var h=new Hls();h.loadSource("' + url + '");h.attachMedia(v);h.on(Hls.Events.MANIFEST_PARSED,function(){v.play()});}\n' +
    'else if(v.canPlayType("application/vnd.apple.mpegurl")){v.src="' + url + '";v.play();}\n' +
    '</scr' + 'ipt>\n' +
    '</body></html>';
  iframe.srcdoc = html;
}

function closePlayer() {
  document.getElementById('player-overlay').classList.remove('active');
  if (document.fullscreenElement) {
    document.exitFullscreen();
  }
  document.getElementById('player-frame').src = '';
  document.getElementById('player-frame').srcdoc = '';
  const video = document.getElementById('player-video');
  video.pause();
  video.src = '';
  video.style.display = 'none';
  document.getElementById('player-frame').style.display = 'block';
  video.style.objectFit = '';
  video.style.aspectRatio = '';
  document.getElementById('player-frame').style.objectFit = '';
  document.getElementById('player-frame').style.aspectRatio = '';
  if (window._hls) { window._hls.destroy(); window._hls = null; }
}

function toggleAppFullscreen() {
  const btn = document.getElementById('fullscreen-btn');
  if (!document.fullscreenElement) {
    // Try fullscreen on the whole document
    const el = document.documentElement;
    const req = el.requestFullscreen || el.webkitRequestFullscreen || el.msRequestFullscreen;
    if (req) req.call(el);
    if (btn) btn.title = 'Salir de pantalla completa';
  } else {
    const exit = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen;
    if (exit) exit.call(document);
    if (btn) btn.title = 'Pantalla completa';
  }
}

function togglePlayerFullscreen() {
  // Try fullscreen on the player overlay first (most immersive)
  const overlay = document.getElementById('player-overlay');
  if (!document.fullscreenElement) {
    const el = overlay || document.documentElement;
    const req = el.requestFullscreen || el.webkitRequestFullscreen || el.msRequestFullscreen;
    if (req) req.call(el).catch(() => {
      // Fallback: fullscreen the video element directly
      const video = document.getElementById('player-video');
      const iframe = document.getElementById('player-frame');
      const target = (video.style.display !== 'none') ? video : iframe;
      const req2 = target.requestFullscreen || target.webkitRequestFullscreen;
      if (req2) req2.call(target).catch(()=>{ toggleAppFullscreen(); });
    });
  } else {
    const exit = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen;
    if (exit) exit.call(document);
  }
}

function closeApp() {
  // Try to close the window (works in pywebview and standalone browser)
  if (window.close) {
    window.close();
  }
  // Fallback: try pywebview close
  if (window.pywebview && window.pywebview.close) {
    window.pywebview.close();
  }
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
  if (e.key === 'F11') {
    e.preventDefault();
    toggleAppFullscreen();
  }
  if (e.key === 'Escape') {
    // If player is open, close it first
    const player = document.getElementById('player-overlay');
    if (player && player.classList.contains('active')) {
      closePlayer();
      e.preventDefault();
    }
  }
});

// Track fullscreen changes (F11, ESC, window buttons)
document.addEventListener('fullscreenchange', function() {
  const btn = document.getElementById('fullscreen-btn');
  if (btn) {
    btn.title = document.fullscreenElement ? 'Salir de pantalla completa' : 'Pantalla completa';
  }
});

loadProviders();
</script>
</body>
</html>"""
