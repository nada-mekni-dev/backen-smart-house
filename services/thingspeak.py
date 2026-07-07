import httpx
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CHANNEL_ID   = os.getenv("TS_CHANNEL_ID",   "3412304")
READ_API_KEY = os.getenv("TS_READ_API_KEY",  "9ZS0RJBJ4JR3ZS4R")
BASE_URL     = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds"

def fetch_latest() -> dict | None:
    try:
        url  = f"{BASE_URL}/last.json?api_key={READ_API_KEY}"
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        feed = resp.json()

        # ThingSpeak renvoie parfois un int (ex: -1) si canal vide
        if not isinstance(feed, dict):
            print(f"[ThingSpeak] Réponse inattendue : {feed}")
            return None

        return _parse_feed(feed)
    except Exception as e:
        print(f"[ThingSpeak] Erreur fetch_latest : {e}")
        return None

def fetch_history(results: int = 50) -> list:
    try:
        url  = f"{BASE_URL}.json?api_key={READ_API_KEY}&results={results}"
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        data  = resp.json()

        if not isinstance(data, dict):
            print(f"[ThingSpeak] Réponse inattendue : {data}")
            return []

        feeds = data.get("feeds", [])

        # Filtrer uniquement les dicts valides
        parsed = []
        for f in feeds:
            if not isinstance(f, dict):
                continue
            result = _parse_feed(f)
            if result:
                parsed.append(result)
        return parsed

    except Exception as e:
        print(f"[ThingSpeak] Erreur fetch_history : {e}")
        return []

def _parse_feed(feed: dict) -> dict | None:
    try:
        # Ignorer les entrées avec tous les champs vides
        if not any(feed.get(f"field{i}") for i in range(1, 5)):
            return None

        return {
            "temperature": float(feed.get("field1") or 0),
            "humidity":    float(feed.get("field2") or 0),
            "presence":    str(feed.get("field3") or "0").strip() == "1",
            "light_level": int(float(feed.get("field4") or 0)),
            "timestamp":   feed.get("created_at", datetime.utcnow().isoformat()),
            "entry_id":    feed.get("entry_id")
        }
    except Exception as e:
        print(f"[ThingSpeak] Erreur parsing feed {feed} : {e}")
        return None