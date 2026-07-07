from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SensorData(BaseModel):
    """Données envoyées par l'ESP32"""
    temperature: float          # DHT22 - °C
    humidity: float             # DHT22 - %
    presence: bool              # PIR - True/False
    light_level: int            # Potentiomètre - 0 à 100 (%)
    timestamp: Optional[datetime] = None

class CommandRequest(BaseModel):
    """Commande textuelle envoyée par l'utilisateur au LLM"""
    instruction: str            # Ex: "Éteins la lumière du salon"

class CommandResponse(BaseModel):
    """Réponse du LLM avec l'action à exécuter"""
    instruction: str
    action: str                 # Ex: "turn_off"
    device: str                 # Ex: "light_salon"
    explanation: str            # Explication en langage naturel
    timestamp: datetime

class DeviceState(BaseModel):
    """État actuel d'un équipement"""
    device_id: str
    device_name: str
    state: str                  # "on" / "off" / valeur numérique
