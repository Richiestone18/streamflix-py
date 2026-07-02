"""FastAPI server for streamflix-py."""
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from .providers.cinecalidad import CineCalidadProvider
from .providers import PROVIDERS

app = FastAPI(title="Streamflix API")


@app.get("/")
async def root():
    return {"message": "Streamflix API", "providers": [p.name for p in PROVIDERS]}


@app.get("/api/providers")
async def list_providers():
    results = []
    for p in PROVIDERS:
        results.append({
            "name": p.name,
            "base_url": p.base_url,
            "language": p.language,
        })
    return {"providers": results}


@app.get("/api/tvshows/{provider_name}")
async def get_tv_shows(provider_name: str, page: int = Query(1, ge=1)):
    from . import get_provider
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
    from . import get_provider
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
    from . import get_provider
    p = get_provider(provider_name)
    if not p:
        return {"error": f"Provider '{provider_name}' not found"}
    servers = await p.get_servers(id)
    return {"provider": provider_name, "results": [
        {"name": s.name, "url": s.id} for s in servers
    ]}


@app.get("/api/search/{provider_name}")
async def search(provider_name: str, q: str = Query(""), page: int = Query(1, ge=1)):
    from . import get_provider
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
    from . import get_provider
    p = get_provider(provider_name)
    if not p:
        return {"error": f"Provider '{provider_name}' not found"}
    results = await p.get_genre(id, page)
    return {"provider": provider_name, "genre": id, "results": [
        {"id": m.id, "title": m.title, "poster": m.poster, "year": m.year}
        for m in results
    ]}


@app.get("/browse", response_class=HTMLResponse)
async def browse():
    return """<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Streamflix</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0f0f0f;color:#eee}
header{background:#1a1a2e;padding:1rem 2rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem}
header h1{color:#e94560;font-size:1.5rem;cursor:pointer}
.search-box{display:flex;gap:.5rem}
.search-box input{background:#16213e;border:1px solid #0f3460;color:#eee;padding:.5rem 1rem;border-radius:6px;width:250px;outline:0}
.search-box input:focus{border-color:#e94560}
.search-box button{background:#e94560;color:#fff;border:0;padding:.5rem 1rem;border-radius:6px;cursor:pointer}
nav{display:flex;gap:.5rem;flex-wrap:wrap;padding:.75rem 2rem;border-bottom:1px solid #1a1a2e}
nav button{background:#16213e;color:#eee;border:1px solid #0f3460;padding:.4rem .8rem;border-radius:6px;cursor:pointer;font-size:.85rem}
nav button:hover{background:#0f3460}
nav button.active{background:#e94560;border-color:#e94560}
#genres{display:flex;gap:.4rem;flex-wrap:wrap;padding:.5rem 2rem;background:#111;display:none}
#genres.show{display:flex}
#genres button{background:#0f3460;color:#aaa;border:0;padding:.25rem .6rem;border-radius:4px;cursor:pointer;font-size:.8rem}
#genres button:hover{color:#fff;background:#e94560}
main{display:grid;grid-template-columns:repeat(auto-fill,minmax(165px,1fr));gap:1rem;padding:1rem 2rem}
.card{background:#1a1a2e;border-radius:8px;overflow:hidden;cursor:pointer;transition:transform .2s;position:relative}
.card:hover{transform:scale(1.03)}
.card img{width:100%;aspect-ratio:2/3;object-fit:cover;display:block}
.card .title{padding:.5rem;font-size:.85rem;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#sentinel{height:1px;width:100%}
footer{text-align:center;padding:2rem;color:#333;font-size:.8rem}
#player-overlay{display:none;position:fixed;inset:0;background:#000;z-index:100;flex-direction:column}
#player-overlay.active{display:flex}
#player-overlay .top{display:flex;justify-content:space-between;align-items:center;padding:.5rem 1rem;background:#111}
#player-overlay .top .info{display:flex;align-items:center;gap:.5rem}
#player-overlay .top button{background:0;border:0;color:#eee;font-size:1.2rem;cursor:pointer;padding:.3rem .6rem}
#player-overlay iframe{flex:1;border:0;width:100%}
.server-list{display:flex;gap:.3rem;flex-wrap:wrap}
.server-list button{background:#16213e;color:#ddd;border:1px solid #0f3460;padding:.2rem .5rem;border-radius:4px;cursor:pointer;font-size:.75rem}
.server-list button:hover{background:#e94560}
#loader{text-align:center;padding:3rem;color:#666}
#no-results{text-align:center;padding:3rem;color:#666;grid-column:1/-1}
#load-more{display:none;margin:1.5rem auto;padding:.75rem 2rem;background:#e94560;color:#fff;border:0;border-radius:8px;cursor:pointer;font-size:1rem}
#load-more.show{display:block}
#load-more:hover{background:#d63851}
#load-more:disabled{background:#555;cursor:default}
</style></head>
<body>
<header>
  <h1 onclick="location.reload()">🎬 Streamflix</h1>
  <div class="search-box">
    <input id="search-input" placeholder="Buscar..." onkeydown="if(event.key==='Enter')doSearch()">
    <button onclick="doSearch()">🔍</button>
  </div>
</header>
<nav id="providers"></nav>
<div id="genres"></div>
<main id="content"><p id="loader">Cargando...</p></main>
<button id="load-more" onclick="loadMore()" class="show">Cargar más</button>
<footer>Streamflix · Python backend</footer>
<div id="player-overlay">
  <div class="top">
    <div class="info"><span id="player-title"></span></div>
    <div><button onclick="closePlayer()">✕ Cerrar</button></div>
  </div>
  <div class="server-list" id="server-buttons" style="padding:.5rem 1rem;background:#111"></div>
  <iframe id="player-frame" allowfullscreen allow="autoplay"></iframe>
</div>
<script>
let currentProvider = '';
let currentPage = 1;
let currentMode = 'movies'; // 'movies' | 'genre' | 'search'
let currentGenreId = '';
let currentSearchQ = '';
let isLoading = false;

async function loadProviders(){
  const r=await fetch('/api/providers');
  const d=await r.json();
  const nav=document.getElementById('providers');
  nav.innerHTML='<button onclick="showGenres()">🎭 Géneros</button>'+
    d.providers.map(p=>`<button onclick="loadContent('${p.name}')">${p.name}</button>`).join('');
  if(d.providers.length) loadContent(d.providers[0].name);
}

async function showGenres(){
  document.getElementById('search-input').value='';
  if(!currentProvider)return;
  const r=await fetch(`/api/search/${currentProvider}?q=`);
  const d=await r.json();
  const genres=d.results.filter(i=>i.type==='genre');
  const g=document.getElementById('genres');
  g.innerHTML=genres.map(x=>`<button onclick="loadGenre('${x.id}')">${x.name}</button>`).join('');
  g.classList.toggle('show');
}

async function loadGenre(id){
  currentGenreId=id;
  currentMode='genre';
  currentPage=1;
  document.getElementById('genres').classList.remove('show');
  document.getElementById('content').innerHTML='<p id="loader">Cargando...</p>';
  document.getElementById('load-more').classList.remove('show');
  const r=await fetch(`/api/genre/${currentProvider}?id=${encodeURIComponent(id)}&page=1`);
  const d=await r.json();
  renderContent(d.results, d.total||d.results.length);
  // Prefetch next pages
  if(d.results.length>0) currentPage=2;
}

async function loadContent(provider){
  currentProvider=provider;
  currentMode='movies';
  currentPage=1;
  document.getElementById('search-input').value='';
  document.getElementById('genres').classList.remove('show');
  document.getElementById('content').innerHTML='<p id="loader">Cargando...</p>';
  document.getElementById('load-more').classList.remove('show');
  const r=await fetch(`/api/movies/${provider}?page=1`);
  const d=await r.json();
  renderContent(d.results, d.total||d.results.length);
  if(d.results.length>0) currentPage=2;
}

async function doSearch(){
  const q=document.getElementById('search-input').value.trim();
  document.getElementById('genres').classList.remove('show');
  document.getElementById('load-more').classList.remove('show');
  if(!q){loadContent(currentProvider);return}
  currentMode='search';
  currentSearchQ=q;
  currentPage=1;
  document.getElementById('content').innerHTML='<p id="loader">Buscando...</p>';
  const r=await fetch(`/api/search/${currentProvider}?q=${encodeURIComponent(q)}&page=1`);
  const d=await r.json();
  const genres=d.results.filter(i=>i.type==='genre');
  const items=d.results.filter(i=>i.type!=='genre');
  if(genres.length&&!items.length){
    const g=document.getElementById('genres');
    g.innerHTML=genres.map(x=>`<button onclick="loadGenre('${x.id}')">${x.name}</button>`).join('');
    g.classList.add('show');
    document.getElementById('content').innerHTML='<p id="no-results">Sin resultados — selecciona un género</p>';
    return;
  }
  renderContent(items, d.total||items.length);
  if(items.length>0) currentPage=2;
}

async function loadMore(){
  if(isLoading) return;
  isLoading=true;
  const btn=document.getElementById('load-more');
  btn.textContent='Cargando...';
  btn.disabled=true;

  let url;
  if(currentMode==='genre')
    url=`/api/genre/${currentProvider}?id=${encodeURIComponent(currentGenreId)}&page=${currentPage}`;
  else if(currentMode==='search')
    url=`/api/search/${currentProvider}?q=${encodeURIComponent(currentSearchQ)}&page=${currentPage}`;
  else
    url=`/api/movies/${currentProvider}?page=${currentPage}`;

  const r=await fetch(url);
  const d=await r.json();

  if(!d.results||!d.results.length){
    btn.textContent='No hay más resultados';
    btn.disabled=true;
    isLoading=false;
    return;
  }

  const main=document.getElementById('content');
  for(const m of d.results){
    if(m.type==='genre') continue;
    const card=document.createElement('div');
    card.className='card';
    card.innerHTML=`<img src="${m.poster||''}" alt="${m.title}" loading="lazy" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22300%22><rect fill=%22%23333%22 width=%22200%22 height=%22300%22/><text x=%2250%%22 y=%2250%%22 text-anchor=%22middle%22 fill=%22%23666%22 font-size=%2214%22>${m.title.replace(/'/g,'')}</text></svg>'"><div class="title">${m.title}</div>`;
    card.onclick=()=>loadServers(m.id);
    main.appendChild(card);
  }

  currentPage++;
  btn.textContent=`Cargar más (página ${currentPage})`;
  btn.disabled=false;
  isLoading=false;
}

function renderContent(items, total){
  const main=document.getElementById('content');
  if(!items.length){main.innerHTML='<p id="no-results">Sin resultados</p>';return}
  main.innerHTML='';
  for(const m of items){
    if(m.type==='genre') continue;
    const card=document.createElement('div');
    card.className='card';
    card.innerHTML=`<img src="${m.poster||''}" alt="${m.title}" loading="lazy" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22300%22><rect fill=%22%23333%22 width=%22200%22 height=%22300%22/><text x=%2250%%22 y=%2250%%22 text-anchor=%22middle%22 fill=%22%23666%22 font-size=%2214%22>${m.title.replace(/'/g,'')}</text></svg>'"><div class="title">${m.title}</div>`;
    card.onclick=()=>loadServers(m.id);
    main.appendChild(card);
  }
  const btn=document.getElementById('load-more');
  btn.textContent=`Cargar más (página 2)`;
  btn.disabled=false;
  btn.classList.add('show');
}

async function loadServers(id){
  const overlay=document.getElementById('player-overlay');
  document.getElementById('player-frame').src='';
  const r=await fetch(`/api/servers/${currentProvider}?id=${encodeURIComponent(id)}`);
  const d=await r.json();
  if(!d.results||!d.results.length){alert('Sin servidores');return}
  const sb=document.getElementById('server-buttons');
  sb.innerHTML=d.results.map((s,i)=>`<button onclick="playServer(${i})">${s.name}</button>`).join('');
  document.getElementById('player-title').textContent=d.results[0].name;
  document.getElementById('player-frame').src=d.results[0].url;
  overlay.classList.add('active');
}

function playServer(idx){
  (async()=>{
    const r=await fetch('/api/servers/'+currentProvider+'?id='+encodeURIComponent(document.getElementById('player-frame').dataset.id||''));
    const d=await r.json();
    if(d.results&&d.results[idx]){
      document.getElementById('player-title').textContent=d.results[idx].name;
      document.getElementById('player-frame').src=d.results[idx].url;
    }
  })()
}

function closePlayer(){
  document.getElementById('player-overlay').classList.remove('active');
  document.getElementById('player-frame').src='';
}
loadProviders();
</script>
</body></html>"""