"""
IW-10 GoogleMaps — Google Maps Local Results
Iron Warrior #10 — Local SEO, NAP + reviews.
Aucun dédié sur RapidAPI.
"""
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import sys
sys.path.insert(0, '/home/user/iron_warriors/shared')
from base import create_app, fetch_html, clean_text, get_timestamp, measure_latency
import time

app = create_app("IW-10 GoogleMaps", "Google Maps local results — local SEO, NAP + reviews")

class LocalResult(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    rating: Optional[str] = None
    reviews_count: Optional[str] = None
    url: Optional[str] = None
    category: Optional[str] = None
    hours: Optional[str] = None
    position: int

class LocalResponse(BaseModel):
    query: str
    engine: str
    results: List[LocalResult]
    timestamp: str
    latency_ms: int

@app.get("/search", response_model=LocalResponse)
async def google_maps(
    q: str = Query(..., description="Local search query (e.g. 'coffee shop paris')"),
    num: int = Query(20, ge=1, le=50),
    gl: str = Query("us"),
    hl: str = Query("en"),
):
    start = time.time()
    url = f"https://www.google.com/search?q={quote_plus(q)}&tbm=lcl&num={num}&gl={gl}&hl={hl}"
    try:
        html = await fetch_html(url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Google Maps fetch failed: {e}")

    soup = BeautifulSoup(html, 'html.parser')
    results = []
    seen = set()

    # Local pack results
    for div in soup.find_all('div', class_='rllt__details') or soup.find_all('div', class_='dbg0pd'):
        name_tag = div.find_previous('div', class_='dbg0pd') or div.find('div', class_='dbg0pd')
        rating_tag = div.find('span', class_='BTtC6e')
        reviews_tag = div.find('span', class_='YrbPBe')
        address_parts = div.find_all('span')
        link = div.find_previous('a', href=True) or div.find('a', href=True)

        name = clean_text(name_tag.get_text()) if name_tag else ""
        if name and name not in seen:
            seen.add(name)
            address = " ".join(clean_text(s.get_text()) for s in address_parts if s.get_text())
            results.append(LocalResult(
                name=name,
                address=address if address else None,
                rating=clean_text(rating_tag.get_text()) if rating_tag else None,
                reviews_count=clean_text(reviews_tag.get_text()) if reviews_tag else None,
                url=link['href'] if link and link.get('href', '').startswith('http') else None,
                position=len(results) + 1,
            ))
            if len(results) >= num:
                break

    # Fallback: parse via aria-label
    if not results:
        for a in soup.find_all('a', {'aria-label': True}):
            label = a.get('aria-label', '')
            if label and 'stars' not in label.lower() and label not in seen:
                seen.add(label)
                results.append(LocalResult(
                    name=clean_text(label),
                    url=a.get('href') if a.get('href', '').startswith('http') else None,
                    position=len(results) + 1,
                ))
                if len(results) >= num:
                    break

    return LocalResponse(
        query=q, engine="google_maps", results=results,
        timestamp=get_timestamp(), latency_ms=measure_latency(start),
    )
