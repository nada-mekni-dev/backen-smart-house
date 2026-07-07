from fastapi import APIRouter, HTTPException
from services.thingspeak import fetch_latest, fetch_history
from database import sensors_col
from datetime import datetime

router = APIRouter()

@router.get("/latest")
def get_latest_data():
    """
    Récupère la dernière mesure depuis ThingSpeak
    et la sauvegarde dans MongoDB.
    """
    data = fetch_latest()
    if not data:
        raise HTTPException(status_code=503, detail="Impossible de récupérer les données ThingSpeak")

    # Sauvegarde dans MongoDB (évite les doublons via entry_id)
    existing = sensors_col.find_one({"entry_id": data["entry_id"]})
    if not existing:
        sensors_col.insert_one(data.copy())

    return data

@router.get("/history")
def get_history(limit: int = 50):
    """
    Récupère les N dernières mesures depuis ThingSpeak
    et les synchronise dans MongoDB.
    """
    records = fetch_history(results=limit)

    if not records:
        # Fallback : retourner ce qu'on a en base
        local = list(sensors_col.find(sort=[("timestamp", -1)]).limit(limit))
        for r in local:
            r["_id"] = str(r["_id"])
        return local

    # Synchroniser dans MongoDB
    for record in records:
        existing = sensors_col.find_one({"entry_id": record["entry_id"]})
        if not existing:
            sensors_col.insert_one(record.copy())

    return records

@router.get("/sync")
def sync_from_thingspeak(results: int = 100):
    """
    Synchronisation manuelle : récupère les N dernières
    mesures ThingSpeak et les stocke dans MongoDB.
    """
    records = fetch_history(results=results)
    inserted = 0
    for record in records:
        existing = sensors_col.find_one({"entry_id": record["entry_id"]})
        if not existing:
            sensors_col.insert_one(record.copy())
            inserted += 1

    return {
        "status": "ok",
        "fetched": len(records),
        "inserted": inserted,
        "message": f"{inserted} nouvelles entrées synchronisées depuis ThingSpeak"
    }