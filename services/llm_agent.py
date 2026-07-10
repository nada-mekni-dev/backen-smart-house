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

SYSTEM_PROMPT = f"""Tu es un assistant domotique intelligent.
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

Tu es un assistant domotique expert. Tu as accès aux données suivantes des capteurs :
- Capteur température : valeur en °C, seuils normal/alerte
- Capteur humidité : valeur en %, seuils normal/alerte
- Capteur mouvement : état actif/inactif, dernière détection
- Capteur luminosité : valeur en lux

Pour chaque question sur un capteur, fournis toujours :
1. La valeur actuelle
2. Si elle est dans la plage normale
3. Une recommandation si nécessaire
4. L'historique récent si disponible
"""

def parse_instruction(instruction: str) -> dict:
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": instruction}
            ],
            max_tokens=200,
            temperature=0.1
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        print(f"[LLM Groq] Réponse : {raw}")
        return json.loads(raw)

    except json.JSONDecodeError:
        print(f"[LLM Groq] JSON invalide : {raw}")
        return {
            "action": "error",
            "device": None,
            "value": None,
            "explanation": "Réponse invalide du LLM."
        }
    except Exception as e:
        print(f"[LLM Groq] Erreur : {e}")
        return {
            "action": "error",
            "device": None,
            "value": None,
            "explanation": f"Erreur LLM : {str(e)}"
        }
