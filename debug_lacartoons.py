import asyncio
from app.providers.lacartoons import LaCartoonsProvider
from bs4 import BeautifulSoup
import re

async def test():
    p = LaCartoonsProvider()
    html = await p._get("https://www.lacartoons.com/serie/capitulo/1?t=1")
    soup = BeautifulSoup(html, "lxml")

    iframes = soup.select("iframe")
    print(f"Iframes: {len(iframes)}")
    for ifr in iframes:
        src = ifr.get("data-src") or ifr.get("src", "") or ifr.get("data-lazy-src", "")
        print(f"  src: {src[:150]}")

    videos = soup.select("video, source")
    print(f"Videos: {len(videos)}")
    for v in videos[:3]:
        print(f"  {v.name}: src={v.get('src','')[:100]}")

    # Buscar URLs de media
    for m in re.finditer(r'https?://[^\s"\'<>]+\.(m3u8|mp4|mkv|webm)', html):
        print(f"  media: {m.group()[:120]}")

    # Buscar scripts relevantes
    for script in soup.select("script"):
        s = script.string or ""
        if any(k in s.lower() for k in ["video", "player", "source", "m3u8", "mp4", "embed"]):
            if "newrelic" not in s.lower() and len(s) < 5000:
                print(f"=== Script ({len(s)} chars) ===")
                print(s[:800])
                print()

asyncio.run(test())
