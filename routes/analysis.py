from fastapi import APIRouter
from services.thingspeak import fetch_latest, fetch_history
from datetime import datetime
from collections import defaultdict

router = APIRouter()


@router.get("/consumption")
def analyze_consumption(results: int = 20):
    """Analyse en temps réel — valeurs actuelles depuis ThingSpeak."""

    # Récupérer la DERNIÈRE mesure pour les valeurs actuelles
    latest = fetch_latest()

    # Récupérer l'historique pour les moyennes
    records = fetch_history(results=results)

    if not records and not latest:
        return {"message": "Pas assez de données ThingSpeak disponibles"}

    # Valeurs actuelles = dernière mesure reçue
    current_temp  = latest["temperature"]  if latest else 0
    current_hum   = latest["humidity"]     if latest else 0
    current_light = latest["light_level"]  if latest else 0
    current_pres  = latest["presence"]     if latest else False

    # Moyennes sur l'historique
    total = len(records)
    if total > 0:
        avg_temp      = round(sum(r["temperature"]  for r in records) / total, 1)
        avg_humidity  = round(sum(r["humidity"]     for r in records) / total, 1)
        avg_light     = round(sum(r["light_level"]  for r in records) / total, 1)
        presence_rate = round(sum(1 for r in records if r["presence"]) / total * 100, 1)
    else:
        avg_temp = current_temp
        avg_humidity = current_hum
        avg_light = current_light
        presence_rate = 100.0 if current_pres else 0.0

    # Heures de forte présence
    hour_presence = defaultdict(int)
    for r in records:
        ts = r.get("timestamp", "")
        try:
            hour = datetime.fromisoformat(ts.replace("Z", "+00:00")).hour
            if r["presence"]:
                hour_presence[hour] += 1
        except Exception:
            pass

    peak_hours = sorted(hour_presence, key=hour_presence.get, reverse=True)[:3]

    return {
        "period":                f"Dernières {total} mesures ThingSpeak",
        "total_records":         total,
        # ✅ Valeurs actuelles (dernière mesure)
        "current_temperature":   current_temp,
        "current_humidity":      current_hum,
        "current_light_level":   current_light,
        "current_presence":      current_pres,
        # Moyennes historique
        "average_temperature":   avg_temp,
        "average_humidity":      avg_humidity,
        "average_light_level":   avg_light,
        "presence_rate_percent": presence_rate,
        "peak_presence_hours":   peak_hours,
        "insight":               _generate_insight(current_temp, presence_rate, current_light),
        "last_updated":          datetime.utcnow().isoformat()
    }


def _generate_insight(temp, presence_rate, light):
    insights = []

    if temp >= 32:
        insights.append(f"🔥 Température très élevée ({temp}°C) — climatisation recommandée.")
    elif temp >= 28:
        insights.append(f"🌡 Température élevée ({temp}°C) — pensez à ventiler.")
    elif temp >= 22:
        insights.append(f"✅ Température confortable ({temp}°C).")
    elif temp >= 18:
        insights.append(f"🌤 Température fraîche ({temp}°C).")
    else:
        insights.append(f"🥶 Température basse ({temp}°C) — chauffage recommandé.")

    if presence_rate >= 60:
        insights.append(f"👤 Forte présence ({presence_rate}%).")
    elif presence_rate >= 20:
        insights.append(f"👤 Présence modérée ({presence_rate}%).")
    else:
        insights.append(f"🏠 Faible présence ({presence_rate}%) — réduisez la consommation.")

    if light >= 70:
        insights.append(f"☀️ Bonne luminosité ({light}%).")
    elif light < 20:
        insights.append(f"🌑 Faible luminosité ({light}%) — pensez à l'éclairage.")

    return " ".join(insights)