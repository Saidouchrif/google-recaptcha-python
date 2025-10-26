# ==========================================================
# 🧠 TP reCAPTCHA v2 avec FastAPI + Jinja2
# ----------------------------------------------------------
# Ce script montre comment intégrer Google reCAPTCHA v2
# dans une petite application FastAPI utilisant Jinja2
# pour le rendu de la page HTML.
# ==========================================================

# --- Importations nécessaires ---
from pathlib import Path
import os
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import httpx


# ==========================================================
# 1️⃣ Définir les chemins absolus du projet
# ----------------------------------------------------------
# On utilise Path pour éviter les erreurs liées aux chemins relatifs.
# - CURRENT_FILE : le fichier courant (main.py)
# - PROJECT_ROOT : dossier racine du projet
# - STATIC_DIR : dossier contenant le CSS, images, etc.
# - TEMPLATES_DIR : dossier contenant les templates Jinja2
# ==========================================================

CURRENT_FILE = Path(__file__).resolve()          # .../server/main.py
PROJECT_ROOT = CURRENT_FILE.parent.parent        # Racine du projet
STATIC_DIR = PROJECT_ROOT / "static"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
ENV_FILE = PROJECT_ROOT / ".env"

# ----------------------------------------------------------
# (Optionnel) Créer les dossiers si besoin
# ----------------------------------------------------------
# STATIC_DIR.mkdir(parents=True, exist_ok=True)
# TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================================
# 2️⃣ Charger les variables d'environnement (.env)
# ----------------------------------------------------------
# Les clés reCAPTCHA (publique et secrète) sont stockées dans
# un fichier .env placé à la racine du projet.
# ==========================================================

load_dotenv(dotenv_path=ENV_FILE)

# Clé secrète du serveur (NE JAMAIS exposer dans le code public)
RECAPTCHA_SECRET = os.getenv("RECAPTCHA_SECRET", "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe")

# Clé publique du site (utilisée côté client dans le HTML)
RECAPTCHA_SITEKEY = os.getenv("RECAPTCHA_SITEKEY", "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI")

# URL officielle de l’API Google reCAPTCHA pour la vérification des tokens
GOOGLE_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

# Debug : Afficher les clés utilisées au démarrage
print(f"🔑 RECAPTCHA_SECRET utilisée : {RECAPTCHA_SECRET[:10]}...")
print(f"🔑 RECAPTCHA_SITEKEY utilisée : {RECAPTCHA_SITEKEY}")
print(f"📁 Fichier .env : {ENV_FILE}")
print(f"📁 Fichier .env existe : {ENV_FILE.exists()}")


# ==========================================================
# 3️⃣ Initialiser l'application FastAPI
# ----------------------------------------------------------
# On configure FastAPI, on monte le dossier "static" pour le CSS,
# et on prépare Jinja2 pour les templates HTML.
# ==========================================================

app = FastAPI(title="TP reCAPTCHA v2 — FastAPI + Jinja")

# Servir les fichiers statiques (CSS, images...) depuis le dossier /static
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Déclarer le dossier des templates (Jinja2)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ==========================================================
# 4️⃣ Page d'accueil (GET /)
# ----------------------------------------------------------
# Cette route affiche la page HTML contenant le formulaire
# et le widget reCAPTCHA. La clé publique (site_key)
# est injectée dynamiquement dans le template.
# ==========================================================

@app.get("/", response_class=PlainTextResponse)
async def home(request: Request):
    """
    Affiche la page d'accueil avec le formulaire sécurisé par reCAPTCHA.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "site_key": RECAPTCHA_SITEKEY,  # Passée à {{ site_key }} dans index.html
        },
    )


# ==========================================================
# 5️⃣ Route /verify — Vérification du reCAPTCHA
# ----------------------------------------------------------
# Cette route reçoit les données du formulaire (email, message)
# ainsi que le token généré par Google reCAPTCHA.
# Elle contacte l'API Google pour valider ce token avant de
# traiter le message.
# ==========================================================

@app.post("/verify", response_class=PlainTextResponse)
async def verify_recaptcha(
    request: Request,
    email: str = Form(...),                       # Champ "email" du formulaire
    message: str = Form(...),                     # Champ "message"
    g_recaptcha_response: str = Form(alias="g-recaptcha-response"),  # Jeton généré par Google
):
    """
    Vérifie le token reCAPTCHA côté serveur.
    """

    # Si aucun token n'est envoyé
    if not g_recaptcha_response:
        raise HTTPException(status_code=400, detail="reCAPTCHA manquant.")

    # Construire la requête vers l’API Google
    payload = {
        "secret": RECAPTCHA_SECRET,              # Clé secrète (serveur)
        "response": g_recaptcha_response,        # Jeton envoyé depuis le client
        "remoteip": request.client.host if request.client else None,  # IP de l'utilisateur (facultatif)
    }

    # Envoyer la requête à Google
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.post(GOOGLE_VERIFY_URL, data=payload)
        data = r.json()

    # Vérification du résultat
    if data.get("success"):
        # ✅ Le CAPTCHA est valide → on peut traiter la demande
        return "✅ Merci ! Votre message a été reçu en toute sécurité."
    else:
        # Le CAPTCHA est invalide → afficher les erreurs retournées par Google
        codes = data.get("error-codes")
        raise HTTPException(status_code=400, detail=f"Échec reCAPTCHA. Codes: {codes}")


# ==========================================================
# 6️⃣ Route /index (optionnelle)
# ----------------------------------------------------------
# Permet de rediriger /index vers la page d'accueil /
# (utile pour compatibilité ou anciens liens)
# ==========================================================

@app.get("/index")
async def index_redirect():
    """Redirige simplement vers la page principale /"""
    return RedirectResponse(url="/", status_code=302)


# ==========================================================
# 7️⃣ Lancement du serveur (en mode développement)
# ----------------------------------------------------------
# Ce bloc permet de lancer le serveur FastAPI directement
# depuis le fichier avec rechargement automatique du code.
# ==========================================================

if __name__ == "__main__":
    import uvicorn
    # ⚙️ Important :
    # Si tu exécutes ce fichier depuis le dossier "server/",
    # utilise "main:app"
    # Si tu exécutes depuis la racine du projet, utilise "server.main:app"
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
