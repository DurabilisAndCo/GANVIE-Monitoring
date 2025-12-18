"""
Génère des données fictives (démo) pour tester le dashboard.
⚠️ À remplacer par la vraie ingestion (Kobo/ODK → API → DB) en production.
"""
from datetime import datetime, timedelta
import random
import numpy as np
import database as db

ZONES = ["Ganvié-Centre", "Sô-Zounko", "Hêvié-Ganvié", "Ahomey-Lokpo", "Vekky", "Djrègbé-Ganvié"]
ACTIVITIES = ["Pêche", "Commerce", "Artisanat", "Tourisme", "Sans emploi", "Autre"]
VULN = ["Faible", "Moyen", "Élevé"]
SEASONS = ["Sèche", "Pluies1", "Pluies2"]

def _rand_point():
    # Approximate bounding box around Ganvié (demo only)
    lat = random.uniform(6.40, 6.48)
    lon = random.uniform(2.38, 2.50)
    return lat, lon

def _risk_level(ph, turb, ecoli):
    # Règles simplifiées : à adapter avec normes locales/OMS
    if ecoli is None:
        return "A_surveiller"
    if ecoli > 100 or turb > 20 or ph < 6.0 or ph > 8.5:
        return "A_risque"
    if ecoli > 10 or turb > 10:
        return "A_surveiller"
    return "Conforme"

def seed(n_households=250, n_samples=40, days=120, target=1000):
    conn = db.get_connection()
    db.init_db(conn)
    db.upsert_target(conn, int(target))

    start = datetime.now() - timedelta(days=int(days))

    for _ in range(int(n_households)):
        dt = start + timedelta(days=random.randint(0, int(days)))
        zone = random.choice(ZONES)
        lat, lon = _rand_point()
        hh_size = random.randint(1, 10)
        act = random.choice(ACTIVITIES)
        vuln = random.choices(VULN, weights=[0.35, 0.40, 0.25])[0]

        water_improved = 1 if random.random() < (0.55 if vuln!="Élevé" else 0.35) else 0
        sanitation = 1 if random.random() < (0.45 if vuln!="Élevé" else 0.25) else 0
        schooling = 1 if random.random() < (0.70 if vuln!="Élevé" else 0.55) else 0
        health = 1 if random.random() < (0.62 if vuln!="Élevé" else 0.45) else 0

        # Needs (binary) — correlated with vuln
        base_p = 0.35 if vuln=="Faible" else (0.55 if vuln=="Moyen" else 0.75)
        needs = {
            "needs_water": int(random.random() < base_p),
            "needs_sanitation": int(random.random() < base_p),
            "needs_housing": int(random.random() < base_p*0.9),
            "needs_education": int(random.random() < base_p*0.8),
            "needs_health": int(random.random() < base_p*0.8),
            "needs_economic": int(random.random() < base_p),
        }

        row = dict(
            collected_at=dt.isoformat(),
            zone=zone,
            lat=lat,
            lon=lon,
            hh_size=hh_size,
            main_activity=act,
            vulnerability=vuln,
            water_improved=water_improved,
            sanitation=sanitation,
            children_schooling=schooling,
            health_access=health,
            notes=None,
            **needs
        )
        db.insert_household(conn, row)

    for _ in range(int(n_samples)):
        dt = start + timedelta(days=random.randint(0, int(days)))
        zone = random.choice(ZONES)
        lat, lon = _rand_point()
        season = random.choice(SEASONS)

        ph = round(random.uniform(5.5, 9.0), 2)
        turb = round(max(0, random.gauss(12, 6)), 1)
        cond = round(max(50, random.gauss(900, 500)), 0)
        ecoli = int(max(0, random.gauss(30, 60)))
        coliforms = int(max(0, random.gauss(80, 120)))

        risk = _risk_level(ph, turb, ecoli)

        row = dict(
            collected_at=dt.isoformat(),
            zone=zone,
            lat=lat,
            lon=lon,
            season=season,
            ph=ph,
            turbidity=turb,
            conductivity=cond,
            e_coli=ecoli,
            coliforms=coliforms,
            risk_level=risk,
            comments=None
        )
        db.insert_water_sample(conn, row)

    conn.close()
    print("✅ Données fictives générées dans ganvie_durable.db")

if __name__ == "__main__":
    seed()