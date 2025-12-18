import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk
from datetime import datetime, date
import database as db

# ------------------ Page config ------------------
st.set_page_config(
    page_title="Ganvié Durable 2030 – Dashboard",
    page_icon="🌊",
    layout="wide",
)

# ------------------ Styling (inspiré du modèle annexe) ------------------
CSS = """
<style>
.block-container {padding-top: 1.2rem;}
.banner {
  border-radius: 18px;
  padding: 18px 18px;
  background: linear-gradient(90deg, rgba(45,51,129,.92), rgba(44,110,161,.86), rgba(68,160,201,.86));
  color: white;
  box-shadow: 0 10px 26px rgba(0,0,0,.22);
  margin-bottom: 14px;
}
.banner-title {font-size: 1.45rem; font-weight: 800; margin: 0;}
.banner-sub {opacity:.92; margin-top: 6px; font-size: .92rem;}
.badge {display:inline-block; padding: 2px 10px; border-radius: 999px; background: rgba(255,255,255,.18); margin-left: 8px; font-size:.78rem;}
.kpi {border-radius: 16px; padding: 14px 14px; border: 1px solid rgba(0,0,0,.08); background: rgba(255,255,255,.85);}
.kpi-label {opacity: .7; font-size:.86rem;}
.kpi-value {font-weight: 800; font-size: 1.45rem; margin-top: 2px;}
.kpi-hint {opacity: .75; font-size:.82rem; margin-top: 6px;}
.rec {border-radius: 14px; padding: 12px 12px; border: 1px solid rgba(0,0,0,.08); background: rgba(255,255,255,.8);}
.rec-title {font-weight: 750; margin-bottom: 6px;}
.tag {display:inline-block; padding: 2px 10px; border-radius: 999px; font-size:.78rem; margin-right: 6px;}
.tag-ok {background: rgba(0,255,127,.12); border: 1px solid rgba(0,255,127,.25);}
.tag-warn {background: rgba(255,165,0,.12); border: 1px solid rgba(255,165,0,.25);}
.tag-bad {background: rgba(255,0,0,.12); border: 1px solid rgba(255,0,0,.25);}
.small-muted {opacity:.75; font-size:.85rem;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ------------------ DB init ------------------
conn = db.get_connection()
db.init_db(conn)

# ------------------ Helpers ------------------
NEED_COLS = {
    "Eau": "needs_water",
    "Assainissement": "needs_sanitation",
    "Habitat": "needs_housing",
    "Éducation": "needs_education",
    "Santé": "needs_health",
    "Activités économiques": "needs_economic",
}

def banner():
    st.markdown(
        """
        <div class="banner">
          <div class="banner-title">🌊 Dashboard Ganvié Durable 2030 – Phase 1 : Diagnostic participatif
            <span class="badge">Powered by Durabilis & Co. Bénin</span>
          </div>
          <div class="banner-sub">Données en temps réel (démo) • Ménages • Eau & Environnement • Cartes • Insights & priorités</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def kpi(col, label, value, hint=""):
    with col:
        st.markdown(f"""
        <div class="kpi">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-hint">{hint}</div>
        </div>
        """, unsafe_allow_html=True)

def tag(level):
    if level == "OK":
        return '<span class="tag tag-ok">OK</span>'
    if level == "ATTENTION":
        return '<span class="tag tag-warn">ATTENTION</span>'
    return '<span class="tag tag-bad">CRITIQUE</span>'

def parse_dt(s):
    try:
        return pd.to_datetime(s)
    except Exception:
        return pd.NaT

def needs_count(df):
    cols = list(NEED_COLS.values())
    for c in cols:
        if c not in df.columns:
            df[c] = 0
    return df[cols].fillna(0).sum(axis=1)

def filtered_data():
    h = db.households_df(conn)
    w = db.water_df(conn)

    if len(h):
        h["collected_at"] = pd.to_datetime(h["collected_at"])
    if len(w):
        w["collected_at"] = pd.to_datetime(w["collected_at"])

    # Sidebar filters (comme décrit dans l’annexe)
    st.sidebar.header("Filtres")
    zones = sorted(list(set(h["zone"].dropna().unique().tolist() + w["zone"].dropna().unique().tolist())))
    zone_sel = st.sidebar.multiselect("Quartier / zone", zones, default=zones)

    if len(h):
        dmin, dmax = h["collected_at"].min().date(), h["collected_at"].max().date()
    elif len(w):
        dmin, dmax = w["collected_at"].min().date(), w["collected_at"].max().date()
    else:
        dmin, dmax = date.today(), date.today()

    dr = st.sidebar.date_input("Période d’analyse", value=(dmin, dmax))
    if isinstance(dr, tuple) and len(dr) == 2:
        start, end = dr[0], dr[1]
    else:
        start, end = dmin, dmax

    vuln_sel = st.sidebar.multiselect("Niveau de vulnérabilité", ["Faible", "Moyen", "Élevé"], default=["Faible", "Moyen", "Élevé"])
    need_sel = st.sidebar.multiselect("Type de besoin", list(NEED_COLS.keys()), default=list(NEED_COLS.keys()))

    # Apply filters
    if len(h):
        h = h[h["zone"].isin(zone_sel)]
        h = h[(h["collected_at"].dt.date >= start) & (h["collected_at"].dt.date <= end)]
        h = h[h["vulnerability"].isin(vuln_sel)]
        # keep households that have at least one selected need
        sel_cols = [NEED_COLS[n] for n in need_sel]
        if sel_cols:
            h = h[h[sel_cols].fillna(0).sum(axis=1) >= 1]

    if len(w):
        w = w[w["zone"].isin(zone_sel)]
        w = w[(w["collected_at"].dt.date >= start) & (w["collected_at"].dt.date <= end)]

    return h, w, {"zones": zone_sel, "start": start, "end": end, "vuln": vuln_sel, "needs": need_sel}

def compute_kpis(h, target_total):
    if len(h) == 0:
        return dict(
            pct_water=0, pct_san=0, pct_school=0, pct_3needs=0,
            surveyed=0, target=target_total
        )
    pct_water = 100 * h["water_improved"].fillna(0).mean()
    pct_san = 100 * h["sanitation"].fillna(0).mean()
    pct_school = 100 * h["children_schooling"].fillna(0).mean()
    needc = needs_count(h)
    pct_3needs = 100 * (needc >= 3).mean()
    return dict(
        pct_water=pct_water,
        pct_san=pct_san,
        pct_school=pct_school,
        pct_3needs=pct_3needs,
        surveyed=len(h),
        target=target_total
    )

def top_zones(h):
    if len(h) == 0:
        return pd.DataFrame(columns=["zone", "vuln_elevee_pct", "sans_san_pct", "besoins_moy"])
    tmp = h.copy()
    tmp["need_count"] = needs_count(tmp)
    g = tmp.groupby("zone").agg(
        vuln_elevee_pct=("vulnerability", lambda s: 100*(s=="Élevé").mean()),
        sans_san_pct=("sanitation", lambda s: 100*(s.fillna(0)==0).mean()),
        besoins_moy=("need_count", "mean"),
        menages=("household_id","count")
    ).reset_index()
    g["score"] = g["vuln_elevee_pct"]*0.45 + g["sans_san_pct"]*0.35 + g["besoins_moy"]*10*0.20
    return g.sort_values("score", ascending=False)

def water_map(w):
    if len(w) == 0 or w[["lat","lon"]].dropna().empty:
        st.info("Aucun point d’eau géolocalisé sur la période / filtres.")
        return
    df = w.dropna(subset=["lat","lon"]).copy()
    color = {
        "Conforme": [0, 200, 120, 180],
        "A_surveiller": [255, 165, 0, 180],
        "A_risque": [255, 0, 0, 180],
    }
    df["color"] = df["risk_level"].map(color).fillna([120,120,120,180])
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_fill_color="color",
        get_radius=55,
        pickable=True,
    )
    view_state = pdk.ViewState(latitude=float(df["lat"].mean()), longitude=float(df["lon"].mean()), zoom=11, pitch=0)
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "Zone: {zone}\nRisque: {risk_level}\npH: {ph}\nTurbidité: {turbidity}\nE. coli: {e_coli}"},
    )
    st.pydeck_chart(deck, use_container_width=True)

def households_map(h):
    if len(h) == 0 or h[["lat","lon"]].dropna().empty:
        st.info("Aucun ménage géolocalisé sur la période / filtres.")
        return
    df = h.dropna(subset=["lat","lon"]).copy()
    df["need_count"] = needs_count(df)
    # scale to colors (blue gradients)
    def col(n):
        if n >= 4: return [45,51,129,170]
        if n == 3: return [44,110,161,170]
        if n == 2: return [68,160,201,170]
        return [170, 200, 220, 150]
    df["color"] = df["need_count"].apply(col)
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_fill_color="color",
        get_radius=25,
        pickable=True,
    )
    view_state = pdk.ViewState(latitude=float(df["lat"].mean()), longitude=float(df["lon"].mean()), zoom=11, pitch=0)
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "Zone: {zone}\nVulnérabilité: {vulnerability}\nBesoins (#): {need_count}"},
    )
    st.pydeck_chart(deck, use_container_width=True)

def insights(h, w):
    recs = []
    if len(h):
        k = compute_kpis(h, db.get_target(conn))
        if k["pct_water"] < 50:
            recs.append(("CRITIQUE", "Accès à l’eau améliorée < 50% : prioriser interventions WASH sur zones à score élevé."))
        elif k["pct_water"] < 70:
            recs.append(("ATTENTION", "Accès à l’eau à surveiller : cibler les zones où la vulnérabilité est élevée."))
        if k["pct_san"] < 40:
            recs.append(("CRITIQUE", "Assainissement faible : lancer actions rapides (latrines, sensibilisation, gestion déchets)."))
        if k["pct_3needs"] > 35:
            recs.append(("ATTENTION", "Beaucoup de ménages expriment ≥3 besoins : planifier un paquet d’investissements multi-secteurs par zone."))

        tz = top_zones(h).head(5)
        if len(tz):
            recs.append(("OK", f"Top zones prioritaires (score composite): {', '.join(tz['zone'].tolist())}."))

    if len(w):
        risk_share = w["risk_level"].value_counts(normalize=True) * 100
        if risk_share.get("A_risque", 0) > 25:
            recs.append(("CRITIQUE", "Qualité de l’eau : forte proportion de points à risque. Activer plan de prévention (traitement, points alternatifs, alertes)."))
        elif risk_share.get("A_surveiller", 0) > 40:
            recs.append(("ATTENTION", "Qualité de l’eau : plusieurs points à surveiller. Renforcer la fréquence des prélèvements en zones sensibles."))

    if not recs:
        recs.append(("OK", "Aucun signal critique sur les filtres actuels. Continuer la collecte et consolider la couverture des zones."))

    for lvl, txt in recs[:6]:
        st.markdown(f'<div class="rec"><div class="rec-title">{tag(lvl)} {txt}</div><div class="small-muted">Recommandation automatique (règles simples) – à valider par les parties prenantes.</div></div>', unsafe_allow_html=True)

def report_pdf_bytes(meta, kpis, tz_df):
    # PDF minimal (sans images) pour rester léger sur Streamlit Cloud
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buff = BytesIO()
    c = canvas.Canvas(buff, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Ganvié Durable 2030 – Note de synthèse (extrait)")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Période: {meta['start']} → {meta['end']} | Zones: {', '.join(meta['zones']) if meta['zones'] else '—'}")
    y -= 26

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Indicateurs clés")
    y -= 16
    c.setFont("Helvetica", 10)
    lines = [
        f"• Accès à une source d’eau améliorée: {kpis['pct_water']:.1f}%",
        f"• Ménages avec dispositif d’assainissement: {kpis['pct_san']:.1f}%",
        f"• Scolarisation (proxy): {kpis['pct_school']:.1f}%",
        f"• Ménages déclarant ≥3 besoins: {kpis['pct_3needs']:.1f}%",
        f"• Ménages enquêtés (filtres): {kpis['surveyed']} / cible: {kpis['target']}",
    ]
    for ln in lines:
        c.drawString(50, y, ln); y -= 14

    y -= 8
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Top zones prioritaires (score composite)")
    y -= 16
    c.setFont("Helvetica", 9)

    if tz_df is None or tz_df.empty:
        c.drawString(50, y, "—"); y -= 14
    else:
        for _, r in tz_df.head(10).iterrows():
            c.drawString(50, y, f"- {r['zone']} | vuln. élevée: {r['vuln_elevee_pct']:.0f}% | sans assain.: {r['sans_san_pct']:.0f}% | besoins moy.: {r['besoins_moy']:.2f}")
            y -= 12
            if y < 80:
                c.showPage()
                y = height - 60

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(40, 40, "Document généré automatiquement depuis le dashboard (démo). À compléter avec cartes/graphes sur version finale.")
    c.save()
    buff.seek(0)
    return buff.getvalue()

# ------------------ UI ------------------
banner()

h, w, meta = filtered_data()
target_total = db.get_target(conn)
k = compute_kpis(h, target_total)

tabs = st.tabs(["Accueil – Vue d’ensemble", "Diagnostic ménages", "Eau & Environnement", "Cartes & Zones", "Insights & Priorités", "Rapport automatisé"])

# 1) Accueil
with tabs[0]:
    c1, c2, c3, c4, c5 = st.columns(5)
    kpi(c1, "% accès eau améliorée", f"{k['pct_water']:.1f}%", "Moyenne sur ménages filtrés")
    kpi(c2, "% assainissement", f"{k['pct_san']:.1f}%", "Moyenne sur ménages filtrés")
    kpi(c3, "Taux de scolarisation (proxy)", f"{k['pct_school']:.1f}%", "Au moins 1 enfant scolarisé")
    kpi(c4, "% ménages ≥ 3 besoins", f"{k['pct_3needs']:.1f}%", "Indicateur de multi‑vulnérabilité")
    kpi(c5, "Ménages enquêtés", f"{k['surveyed']}/{k['target']}", "Cible paramétrable")

    st.markdown("### Évolution de la collecte (ménages)")
    if len(h):
        hh_daily = h.set_index("collected_at").resample("D")["household_id"].count().reset_index()
        hh_daily["cumul"] = hh_daily["household_id"].cumsum()
        fig = px.line(hh_daily, x="collected_at", y="cumul", markers=True, labels={"collected_at":"Date", "cumul":"Ménages (cumul)"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée ménage sur la période / filtres.")

    st.markdown("### Répartition des besoins (ménages)")
    if len(h):
        need_sum = {k: int(h[v].fillna(0).sum()) for k, v in NEED_COLS.items()}
        df_need = pd.DataFrame({"Besoin": list(need_sum.keys()), "Nombre": list(need_sum.values())}).sort_values("Nombre", ascending=False)
        fig2 = px.bar(df_need, x="Besoin", y="Nombre", labels={"Nombre":"Nombre de ménages"})
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Aucune donnée ménage pour calculer la répartition des besoins.")

# 2) Diagnostic ménages
with tabs[1]:
    st.markdown("### Comparaisons par zone")
    if len(h):
        tmp = h.copy()
        tmp["need_count"] = needs_count(tmp)
        g = tmp.groupby("zone").agg(
            pct_eau=("water_improved", "mean"),
            pct_san=("sanitation", "mean"),
            vuln_elevee=("vulnerability", lambda s: (s=="Élevé").mean()),
            besoins_moy=("need_count", "mean"),
            menages=("household_id","count")
        ).reset_index()
        g["pct_eau"] *= 100; g["pct_san"] *= 100; g["vuln_elevee"] *= 100
        fig = px.bar(g.sort_values("pct_eau"), x="zone", y="pct_eau", labels={"pct_eau":"% accès eau améliorée", "zone":"Zone"})
        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            figb = px.bar(g.sort_values("vuln_elevee"), x="zone", y="vuln_elevee", labels={"vuln_elevee":"% vulnérabilité élevée", "zone":"Zone"})
            st.plotly_chart(figb, use_container_width=True)
        with c2:
            figc = px.bar(g.sort_values("besoins_moy"), x="zone", y="besoins_moy", labels={"besoins_moy":"Besoins moyens (0–6)", "zone":"Zone"})
            st.plotly_chart(figc, use_container_width=True)

        st.markdown("### Lien activité ↔ besoins (scatter)")
        figd = px.scatter(tmp, x="hh_size", y="need_count", color="main_activity", hover_data=["zone","vulnerability"], labels={"hh_size":"Taille ménage", "need_count":"Nombre de besoins"})
        st.plotly_chart(figd, use_container_width=True)

        st.markdown("### Top zones prioritaires (liste)")
        tz = top_zones(h).head(5)[["zone","menages","vuln_elevee_pct","sans_san_pct","besoins_moy","score"]]
        st.dataframe(tz, use_container_width=True)
    else:
        st.info("Aucune donnée ménage sur la période / filtres.")

# 3) Eau & Environnement
with tabs[2]:
    st.markdown("### Carte des points de prélèvement (codes couleur conforme / à surveiller / à risque)")
    water_map(w)

    st.markdown("### Évolution saisonnière (exemples)")
    if len(w):
        c1, c2 = st.columns(2)
        with c1:
            fig = px.box(w, x="season", y="turbidity", points="all", labels={"season":"Saison", "turbidity":"Turbidité"})
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.box(w, x="season", y="e_coli", points="all", labels={"season":"Saison", "e_coli":"E. coli (CFU/100ml)"})
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("### Fiches automatiques (derniers prélèvements)")
        latest = w.sort_values("collected_at").groupby(["zone"]).tail(1).sort_values("risk_level")
        st.dataframe(latest[["zone","collected_at","season","ph","turbidity","conductivity","e_coli","risk_level"]], use_container_width=True)
    else:
        st.info("Aucune donnée d’eau sur la période / filtres.")

# 4) Cartes & Zones
with tabs[3]:
    st.markdown("### Carte des ménages (couleur = intensité des besoins)")
    households_map(h)

    st.markdown("### Synthèse par zone")
    if len(h):
        tz = top_zones(h)[["zone","menages","vuln_elevee_pct","sans_san_pct","besoins_moy","score"]]
        st.dataframe(tz, use_container_width=True)
    else:
        st.info("Aucune donnée ménage sur la période / filtres.")

# 5) Insights
with tabs[4]:
    st.markdown("### Tendances & recommandations automatiques (règles)")
    insights(h, w)

    st.markdown("### Scénario simple (démo) : améliorer l’accès à l’eau dans 1–3 zones")
    if len(h):
        tz = top_zones(h).head(6)
        zones = tz["zone"].tolist()
        pick = st.multiselect("Zones ciblées (simulation)", zones, default=zones[:2])
        delta = st.slider("Gain d’accès eau améliorée (points de %)", min_value=0, max_value=40, value=15, step=5)
        cur = compute_kpis(h, target_total)["pct_water"]
        sim = min(100.0, cur + (delta * (len(pick)/max(1,len(zones)))))
        st.write(f"Accès eau actuel: **{cur:.1f}%** → simulé: **{sim:.1f}%** (approx.)")
        st.caption("Simulation indicative (démo) : la version finale doit utiliser un modèle d’impact par zone/ménage.")
    else:
        st.info("Aucune donnée ménage pour la simulation.")

# 6) Rapport
with tabs[5]:
    st.markdown("### Générer un rapport (PDF) – 1 clic")
    st.caption("Dans l’annexe, le dashboard prévoit un export PDF/PPT. Ici: PDF minimal (KPIs + top zones).")
    tz = top_zones(h)
    if st.button("📄 Générer le PDF"):
        pdf_bytes = report_pdf_bytes(meta, k, tz)
        st.download_button(
            label="Télécharger la note PDF",
            data=pdf_bytes,
            file_name="ganvie_durable_note_synthese.pdf",
            mime="application/pdf"
        )

    st.markdown("### Exports données")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ Export ménages (CSV)", data=h.to_csv(index=False).encode("utf-8"), file_name="households_filtered.csv", mime="text/csv")
    with c2:
        st.download_button("⬇️ Export eau (CSV)", data=w.to_csv(index=False).encode("utf-8"), file_name="water_samples_filtered.csv", mime="text/csv")

st.sidebar.markdown("---")
st.sidebar.subheader("Démo / initialisation")
if st.sidebar.button("🌱 Générer des données fictives"):
    import seed_data
    seed_data.seed()
    st.sidebar.success("Données fictives ajoutées. Rechargez la page.")