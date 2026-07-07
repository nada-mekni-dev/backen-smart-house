from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import sensors, commands, analysis
from fastapi.responses import FileResponse

app = FastAPI(title="Domotique Intelligente API", version="1.0.0")

# Autoriser les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrement des routes
app.include_router(sensors.router, prefix="/sensors", tags=["Capteurs"])
app.include_router(commands.router, prefix="/commands", tags=["Commandes LLM"])
app.include_router(analysis.router, prefix="/analysis", tags=["Analyse"])

@app.get("/")
def root():
    return {"message": "Serveur Domotique opérationnel ✅"}

@app.get("/dashboard")
def serve_dashboard():
    return FileResponse("index.html")
