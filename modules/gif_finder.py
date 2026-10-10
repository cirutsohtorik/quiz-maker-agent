import urllib.request
import urllib.parse
import json
from typing import Optional, Dict
import config


def search_giphy(query: str) -> Optional[Dict[str, str]]:
    """
    Verilen anahtar kelimeye göre Giphy'den en uygun GIF'i çeker.
    Dönen sözlük:
    {
        "id": "...",
        "url": "https://media.../giphy.gif",
        "title": "...",
        "query": query
    }
    """
    if not query:
        query = "funny reaction"
        
    encoded_query = urllib.parse.quote(query)
    api_url = f"https://api.giphy.com/v1/gifs/search?api_key={config.GIPHY_FALLBACK_API_KEY}&q={encoded_query}&limit=3&rating=g"
    
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("data", [])
            if results:
                top_gif = results[0]
                return {
                    "id": top_gif.get("id"),
                    "url": top_gif["images"]["original"]["url"],
                    "downsized_url": top_gif["images"].get("downsized_medium", {}).get("url") or top_gif["images"]["original"]["url"],
                    "title": top_gif.get("title", query),
                    "query": query
                }
    except Exception as e:
        print(f"[Giphy Warning] '{query}' için GIF alınamadı: {e}")
        
    return None
