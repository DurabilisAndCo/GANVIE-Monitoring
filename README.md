# Ganvié Durable 2030 – Dashboard (Streamlit)

Ce dépôt fournit une **base de dashboard** conforme à l'annexe “Modèle de tableau de bord automatisé” de la note de proposition :
- Menu latéral + filtres (période, zone, vulnérabilité, besoins)
- Onglets : Accueil, Diagnostic ménages, Eau & Environnement, Cartes & Zones, Insights & priorités, Rapport (PDF)  
- Base de données locale SQLite (démo) + génération de données fictives

## 1) Lancer en local
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 2) Déployer sur Streamlit Community Cloud
1. Poussez ce dossier sur GitHub
2. Streamlit Cloud → **New app** → choisissez le repo → `app.py` → Deploy

## 3) Base de données
SQLite local: `ganvie_durable.db` (créé automatiquement au lancement).

> Pour un usage multi-utilisateurs et une ingestion temps réel depuis Kobo/ODK, migrez vers Postgres (Supabase/Neon) + API.

## 4) Données de démo
Dans la sidebar, cliquez **“Générer des données fictives”** (ou lancez `python seed_data.py`).

## 5) Structure
- `app.py` : application Streamlit (dashboard)
- `database.py` : schéma + accès SQLite
- `seed_data.py` : génération de données fictives

## 6) À brancher ensuite (phase production)
- Ingestion Kobo/ODK → API (FastAPI) → Postgres/PostGIS
- Couches SIG (GeoJSON) + polygones zones/quartiers
- Rapport PDF/PPT enrichi (cartes + graphes) + authentification