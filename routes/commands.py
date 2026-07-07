from fastapi import APIRouter, HTTPException
from models.schemas import CommandRequest
from services.llm_agent import parse_instruction
from datetime import datetime

router = APIRouter()

# ── État des équipements en mémoire (fallback si MongoDB indisponible) ──
DEVICES_STATE = {
    "light_salon":    {"device_id": "light_salon",    "device_name": "Lumière salon",    "state": "off"},
    "light_bedroom":  {"device_id": "light_bedroom",  "device_name": "Lumière chambre",  "state": "off"},
    "light_kitchen":  {"device_id": "light_kitchen",  "device_name": "Lumière cuisine",  "state": "off"},
    "ac_salon":       {"device_id": "ac_salon",       "device_name": "Climatiseur salon","state": "off"},
    "heater_bedroom": {"device_id": "heater_bedroom", "device_name": "Chauffage chambre","state": "off"},
    "blinds_salon":   {"device_id": "blinds_salon",   "device_name": "Volets salon",     "state": "off"},
}

commands_history = []  # Historique en mémoire

def get_db():
    """Essaie de retourner les collections MongoDB, sinon None."""
    try:
        from database import devices_col, commands_col
        # Test rapide de connexion
        devices_col.find_one()
        return devices_col, commands_col
    except Exception:
        return None, None

@router.post("/execute")
def execute_command(req: CommandRequest):
    """Reçoit une instruction texte, la passe au LLM Claude,
    puis applique l'action sur l'état des équipements."""
    result = parse_instruction(req.instruction)

    if result["action"] == "error":
        raise HTTPException(status_code=500, detail=result["explanation"])

    # Mettre à jour l'état en mémoire
    if result["device"] and result["action"] != "unknown":
        new_state = "on"  if result["action"] == "turn_on"  else \
                    "off" if result["action"] == "turn_off" else \
                    str(result.get("value", ""))

        if result["device"] in DEVICES_STATE:
            DEVICES_STATE[result["device"]]["state"] = new_state

        # Essayer aussi MongoDB si disponible
        try:
            from database import devices_col
            devices_col.update_one(
                {"device_id": result["device"]},
                {"$set": {"state": new_state, "updated_at": datetime.utcnow()}},
                upsert=True
            )
        except Exception:
            pass  # MongoDB indisponible → on utilise la mémoire

    # Enregistrer dans l'historique mémoire
    log = {
        "instruction": req.instruction,
        "action":      result["action"],
        "device":      result["device"],
        "explanation": result["explanation"],
        "timestamp":   datetime.utcnow().isoformat()
    }
    commands_history.append(log)

    # Essayer aussi MongoDB
    try:
        from database import commands_col
        commands_col.insert_one(log.copy())
    except Exception:
        pass

    return {
        "status":      "ok",
        "action":      result["action"],
        "device":      result["device"],
        "explanation": result["explanation"]
    }

@router.get("/history")
def get_command_history(limit: int = 20):
    """Retourne l'historique des commandes."""
    try:
        from database import commands_col
        records = list(commands_col.find(sort=[("timestamp", -1)]).limit(limit))
        for r in records:
            r["_id"] = str(r["_id"])
        return records
    except Exception:
        return list(reversed(commands_history[-limit:]))

@router.get("/devices")
def get_devices_state():
    """Retourne l'état actuel de tous les équipements."""
    try:
        from database import devices_col
        devices = list(devices_col.find())
        for d in devices:
            d["_id"] = str(d["_id"])
        # Fusionner avec l'état en mémoire pour les devices manquants
        db_ids = {d["device_id"] for d in devices}
        for dev_id, dev in DEVICES_STATE.items():
            if dev_id not in db_ids:
                devices.append(dev)
        return devices
    except Exception:
        # Fallback complet sur la mémoire
        return list(DEVICES_STATE.values())