import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY manquante dans .env !")
else:
    print(f"✅ Clé Groq chargée : {GROQ_API_KEY[:20]}...")

client = Groq(api_key=GROQ_API_KEY)

AVAILABLE_DEVICES = {
    "light_salon":    "Lumière du salon",
    "light_bedroom":  "Lumière de la chambre",
    "light_kitchen":  "Lumière de la cuisine",
    "ac_salon":       "Climatiseur du salon",
    "heater_bedroom": "Chauffage de la chambre",
    "blinds_salon":   "Volets du salon",
}

# ---------------------------------------------------------------------------
# 1) PROMPT DE ROUTAGE : décide si la question concerne un appareil ou un capteur
# ---------------------------------------------------------------------------
ROUTER_PROMPT = """Tu es un classifieur d'intentions pour un assistant domotique.
Classe la demande de l'utilisateur dans une seule des trois catégories :
- "device"   -> l'utilisateur veut allumer/éteindre/régler un appareil (lumière, chauffage, clim, volets...)
- "sensor"   -> l'utilisateur pose une question précise sur une mesure (température, humidité, mouvement, luminosité...)
- "greeting" -> salutation, question générale, ou demande de recommandation/résumé de la maison
                (ex: "bonjour", "salut", "que me recommandes-tu aujourd'hui ?", "comment va la maison ?")

Réponds UNIQUEMENT avec ce JSON, sans markdown ni backticks :
{"intent": "device" | "sensor" | "greeting"}
"""

# ---------------------------------------------------------------------------
# 2) PROMPT "DEVICE" : contrôle des appareils -> réponse JSON stricte
# ---------------------------------------------------------------------------
DEVICE_SYSTEM_PROMPT = f"""Tu es un assistant domotique intelligent.
L'utilisateur te donne une instruction en langage naturel pour contrôler la maison.
Réponds UNIQUEMENT avec un JSON valide (sans markdown, sans backticks) :
{{
  "action": "turn_on" | "turn_off" | "set_value",
  "device": "<identifiant>",
  "value": null,
  "explanation": "<confirmation en français>"
}}
Équipements disponibles : {json.dumps(AVAILABLE_DEVICES, ensure_ascii=False)}
Si inconnu : {{"action": "unknown", "device": null, "value": null, "explanation": "<explication>"}}
IMPORTANT : Réponds UNIQUEMENT avec le JSON, rien d'autre.
"""

# ---------------------------------------------------------------------------
# 3) PROMPT "SENSOR" : questions sur les capteurs -> réponse texte structurée
#    Les VRAIES valeurs sont injectées dans le message user, pas devinées par le LLM.
# ---------------------------------------------------------------------------
SENSOR_SYSTEM_PROMPT = """Tu es un assistant domotique expert en analyse de capteurs.
Tu reçois dans le message utilisateur les données réelles des capteurs (valeur, seuils, historique).
Ne jamais inventer de valeurs : utilise uniquement celles fournies.

Pour chaque question sur un capteur, réponds en français avec :
1. La valeur actuelle
2. Si elle est dans la plage normale ou en alerte
3. Une recommandation si nécessaire
4. L'historique récent si disponible dans les données fournies
"""


GREETING_SYSTEM_PROMPT = """Tu es un assistant domotique chaleureux et proactif.
L'utilisateur te salue ou te pose une question générale sur l'état de sa maison.
Tu reçois dans le message utilisateur l'état actuel de tous les capteurs et appareils.

Réponds en français, de façon conviviale et concise (5-8 lignes max) :
1. Salue l'utilisateur brièvement
2. Donne un résumé rapide de l'état de la maison (température, humidité, appareils actifs...)
3. Propose 1 à 3 recommandations concrètes si pertinent (ex: "il fait chaud, veux-tu que j'allume la clim ?")
Ne jamais inventer de valeurs : utilise uniquement celles fournies.
"""


def get_sensor_data() -> dict:
    """
    À REMPLACER par ta vraie source de données (API, base de données, variables capteurs...).
    Doit retourner un dict avec les valeurs actuelles + seuils + historique.
    """
    return {
        "temperature": {"valeur": 24.5, "unite": "°C", "seuil_normal": [18, 26], "historique": [23.8, 24.0, 24.5]},
        "humidite":    {"valeur": 55,   "unite": "%",  "seuil_normal": [30, 60], "historique": [52, 54, 55]},
        "mouvement":   {"etat": "inactif", "derniere_detection": "2026-07-10 14:32"},
        "luminosite":  {"valeur": 320,  "unite": "lux", "historique": [300, 310, 320]},
    }


def classify_intent(instruction: str) -> str:
    """Détermine si la demande concerne un appareil ou un capteur."""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": ROUTER_PROMPT},
                {"role": "user", "content": instruction},
            ],
            max_tokens=20,
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw).get("intent", "device")
    except Exception as e:
        print(f"[Router] Erreur, fallback sur 'device' : {e}")
        return "device"


def parse_instruction(instruction: str) -> dict:
    """Mode contrôle d'appareils -> retourne un dict JSON structuré."""
    raw = None
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": DEVICE_SYSTEM_PROMPT},
                {"role": "user", "content": instruction},
            ],
            max_tokens=200,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        print(f"[LLM Groq - device] Réponse : {raw}")
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"[LLM Groq - device] JSON invalide : {raw}")
        return {
            "action": "error",
            "device": None,
            "value": None,
            "explanation": "Réponse invalide du LLM.",
        }
    except Exception as e:
        print(f"[LLM Groq - device] Erreur : {e}")
        return {
            "action": "error",
            "device": None,
            "value": None,
            "explanation": f"Erreur LLM : {str(e)}",
        }


def ask_sensor(instruction: str) -> str:
    """Mode capteurs -> retourne une réponse texte basée sur les vraies données."""
    data = get_sensor_data()
    user_content = (
        f"Question : {instruction}\n\n"
        f"Données capteurs actuelles (JSON) :\n{json.dumps(data, ensure_ascii=False, indent=2)}"
    )
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SENSOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[LLM Groq - sensor] Erreur : {e}")
        return f"Erreur lors de l'analyse du capteur : {str(e)}"


def ask_greeting(instruction: str) -> str:
    """Mode salutation/recommandation -> résumé convivial de l'état de la maison."""
    data = get_sensor_data()
    user_content = (
        f"Message utilisateur : {instruction}\n\n"
        f"État actuel de la maison (capteurs) :\n{json.dumps(data, ensure_ascii=False, indent=2)}\n\n"
        f"Appareils disponibles : {json.dumps(AVAILABLE_DEVICES, ensure_ascii=False)}"
    )
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": GREETING_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=250,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[LLM Groq - greeting] Erreur : {e}")
        return f"Erreur lors de la génération de la réponse : {str(e)}"


def handle_instruction(instruction: str):
    """Point d'entrée unique : route automatiquement vers le bon mode."""
    intent = classify_intent(instruction)
    print(f"[Router] Intention détectée : {intent}")
    if intent == "sensor":
        return ask_sensor(instruction)
    if intent == "greeting":
        return ask_greeting(instruction)
    return parse_instruction(instruction)


if __name__ == "__main__":
    tests = [
        "Bonjour, que me recommandes-tu aujourd'hui ?",
        "Allume la lumière du salon",
        "Quelle est la température actuelle ?",
        "Éteins le chauffage de la chambre",
        "Est-ce qu'il y a de l'humidité anormale ?",
    ]
    for t in tests:
        print(f"\n--- Instruction : {t} ---")
        result = handle_instruction(t)
        print("Résultat :", result)
