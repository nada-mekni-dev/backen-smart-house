from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

# Connexion avec timeout court pour ne pas bloquer le serveur
try:
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
    # Test rapide
    client.admin.command('ping')
    db = client["domotique"]
    print(f"✅ MongoDB connecté : {MONGO_URL[:40]}...")
except Exception as e:
    print(f"⚠️  MongoDB indisponible : {e}")
    print("⚠️  Le serveur continuera sans base de données.")
    client = None
    db = None

def get_collection(name):
    """Retourne une collection MongoDB ou None si indisponible."""
    if db is None:
        return None
    try:
        return db[name]
    except Exception:
        return None

# Collections
sensors_col  = get_collection("sensors")
commands_col = get_collection("commands")
devices_col  = get_collection("devices")