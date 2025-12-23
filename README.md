# Ganvié Durable 2030 – Dashboard (Streamlit)

Dashboard de monitoring pour le projet **Ganvié Durable 2030** – suivi des ménages et qualité de l'eau à Ganvié, Bénin.

## 🚀 Déploiement sur Streamlit Cloud

1. Fork ou clonez ce repo
2. Allez sur [share.streamlit.io](https://share.streamlit.io)
3. Connectez-vous avec GitHub
4. Cliquez sur **"New app"** → sélectionnez ce repo → `app.py` → **Deploy**

## 💻 Lancer en local

```bash
# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer le dashboard
streamlit run app.py
```

## 📊 Fonctionnalités

- **Vue d'ensemble** : KPIs clés (eau, assainissement, scolarisation)
- **Diagnostic ménages** : Comparaisons par zone, vulnérabilité
- **Eau & Environnement** : Carte des prélèvements, qualité de l'eau
- **Cartes & Zones** : Visualisation géographique des ménages
- **Insights & Priorités** : Recommandations automatiques
- **Rapport automatisé** : Export PDF et CSV

## 🗂️ Structure

```
├── app.py              # Application Streamlit
├── database.py         # Schéma SQLite et accès données
├── seed_data.py        # Génération de données fictives
├── requirements.txt    # Dépendances Python
└── .streamlit/
    └── config.toml     # Configuration Streamlit
```

## ⚠️ Note pour la production

La base SQLite (`ganvie_durable.db`) est locale et éphémère sur Streamlit Cloud.  
Pour un usage en production, migrez vers **Supabase** ou **Neon** (Postgres gratuit).

---

*Powered by Durabilis & Co. Bénin* 🌊