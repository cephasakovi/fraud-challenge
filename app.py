"""
Interface Streamlit — Tableau de bord de détection de fraude (jury INTELO2026).

Le jury lancera :  streamlit run app.py

Contrat technique respecté :
  - on appelle `detect_fraud` / `load_transactions` sans les modifier ;
  - tout le travail de présentation est dans `render_interface()`.

Design : thème sombre « glassmorphism », indicateurs visuels, visualisation 3D
(Plotly), jauge de risque, donut des motifs et globe terrestre 3D des trajets
suspects (Plotly). L'objectif : qu'un public non technique comprenne en un
coup d'œil.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from fraud_detection import detect_fraud, load_transactions

SAMPLE_CSV = Path(__file__).parent / "data" / "sample_transactions.csv"

# Couleurs de la charte.
C_DANGER = "#FF4D6D"
C_SAFE = "#3DD68C"
C_ACCENT = "#7C5CFF"
C_ACCENT2 = "#22D3EE"
C_WARN = "#FFB020"

# Coordonnées (lat, lon) approximatives par code pays ISO-2, pour la carte 3D.
COUNTRY_COORDS = {
    "FR": (46.6, 2.4), "US": (39.8, -98.6), "JP": (36.2, 138.3),
    "GB": (54.0, -2.0), "DE": (51.2, 10.4), "ES": (40.2, -3.7),
    "IT": (42.8, 12.8), "PT": (39.5, -8.0), "BE": (50.6, 4.6),
    "NL": (52.2, 5.3), "IE": (53.2, -8.0), "AT": (47.6, 14.1),
    "FI": (64.0, 26.0), "CH": (46.8, 8.2), "CA": (56.1, -106.3),
    "CN": (35.9, 104.2), "IN": (22.4, 78.9), "BR": (-14.2, -51.9),
    "RU": (61.5, 105.3), "AU": (-25.3, 133.8), "TG": (8.6, 0.8),
    "SN": (14.5, -14.5), "CI": (7.5, -5.5), "BJ": (9.3, 2.3),
    "ML": (17.6, -4.0), "NE": (17.6, 8.1), "BF": (12.2, -1.6),
    "GW": (12.0, -15.0), "MA": (31.8, -7.1), "DZ": (28.0, 1.7),
    "TN": (34.0, 9.6), "EG": (26.8, 30.8), "ZA": (-30.6, 22.9),
    "NG": (9.1, 8.7), "KE": (0.0, 37.9), "AE": (23.4, 53.8),
    "SA": (23.9, 45.1), "TR": (39.0, 35.2), "MX": (23.6, -102.6),
    "AR": (-38.4, -63.6), "GR": (39.1, 21.8), "SE": (60.1, 18.6),
    "NO": (60.5, 8.5), "PL": (51.9, 19.1), "SG": (1.35, 103.8),
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Sora:wght@600;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(124,92,255,0.18), transparent 60%),
    radial-gradient(900px 500px at 110% 10%, rgba(34,211,238,0.14), transparent 55%),
    linear-gradient(180deg, #070A14 0%, #0A0E1A 100%);
}

#MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }

.hero {
  border-radius: 22px;
  padding: 30px 34px;
  margin-bottom: 8px;
  background: linear-gradient(120deg, rgba(124,92,255,0.22), rgba(34,211,238,0.10));
  border: 1px solid rgba(255,255,255,0.10);
  box-shadow: 0 18px 50px rgba(0,0,0,0.45);
}
.hero h1 {
  font-family: 'Sora', sans-serif; font-weight: 800; font-size: 2.1rem;
  margin: 0; letter-spacing: -0.5px;
  background: linear-gradient(90deg, #fff, #C9C2FF 60%, #9BE8F5);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero p { color: #AAB2CF; margin: 8px 0 0; font-size: 0.98rem; }

.kpi {
  border-radius: 18px; padding: 18px 20px; height: 100%;
  background: rgba(255,255,255,0.045);
  border: 1px solid rgba(255,255,255,0.09);
  backdrop-filter: blur(8px);
  box-shadow: 0 10px 30px rgba(0,0,0,0.35);
  transition: transform .15s ease, border-color .15s ease;
}
.kpi:hover { transform: translateY(-3px); border-color: rgba(124,92,255,0.5); }
.kpi .label { color: #9AA3C4; font-size: 0.82rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: .6px; }
.kpi .value { font-family: 'Sora', sans-serif; font-size: 2.0rem; font-weight: 800;
  margin-top: 4px; line-height: 1.1; }
.kpi .sub { color: #7E87A6; font-size: 0.8rem; margin-top: 2px; }

.badge { display:inline-block; padding: 3px 10px; border-radius: 999px;
  font-size: 0.74rem; font-weight: 700; }
.badge.danger { background: rgba(255,77,109,0.16); color: #FF8198;
  border: 1px solid rgba(255,77,109,0.45); }
.badge.safe { background: rgba(61,214,140,0.14); color: #6FE3AC;
  border: 1px solid rgba(61,214,140,0.4); }

.section-title { font-family:'Sora',sans-serif; font-weight:700; font-size:1.15rem;
  margin: 6px 0 2px; color:#EAecF7; }
.section-sub { color:#8B93B2; font-size:0.85rem; margin-bottom:10px; }

div[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden;
  border: 1px solid rgba(255,255,255,0.08); }
</style>
"""


# --------------------------------------------------------------------------- #
#  Préparation des données (fonctions pures, testables sans Streamlit)
# --------------------------------------------------------------------------- #
def build_dataframe(transactions: list[dict], results: list[dict]) -> pd.DataFrame:
    by_id = {t.get("transaction_id"): t for t in transactions}
    rows = []
    for r in results:
        tx = by_id.get(r["transaction_id"], {})
        rows.append({
            "Transaction": r["transaction_id"],
            "Client": tx.get("user_id"),
            "Date": tx.get("timestamp"),
            "Montant": tx.get("amount"),
            "Devise": tx.get("currency"),
            "Commerçant": tx.get("merchant"),
            "Pays": tx.get("country"),
            "Carte présente": tx.get("card_present"),
            "Risque": round(float(r.get("fraud_score", 0.0)) * 100),
            "Suspecte": bool(r.get("is_suspicious")),
            "Explication": r.get("reason", ""),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["_dt"] = pd.to_datetime(df["Date"], errors="coerce", utc=True)
        df["Statut"] = df["Suspecte"].map({True: "Suspecte", False: "Saine"})
    return df


def _jitter(key: str, scale: float = 2.2) -> tuple[float, float]:
    """Petit décalage déterministe pour éviter la superposition des points."""
    h = hashlib.md5(str(key).encode()).hexdigest()
    dx = (int(h[:4], 16) / 65535.0 - 0.5) * scale
    dy = (int(h[4:8], 16) / 65535.0 - 0.5) * scale
    return dx, dy


def build_map_points(df: pd.DataFrame) -> pd.DataFrame:
    pts = []
    for _, r in df.iterrows():
        code = str(r["Pays"]).strip().upper() if isinstance(r["Pays"], str) else None
        if code in COUNTRY_COORDS:
            lat, lon = COUNTRY_COORDS[code]
            dlat, dlon = _jitter(r["Transaction"])
            susp = bool(r["Suspecte"])
            pts.append({
                "lat": lat + dlat, "lon": lon + dlon,
                "tx": r["Transaction"], "client": r["Client"],
                "pays": code, "risque": int(r["Risque"]),
                "montant": float(r["Montant"]) if pd.notna(r["Montant"]) else 0.0,
                "color": [255, 77, 109, 200] if susp else [61, 214, 140, 150],
                "radius": 45000 + (abs(float(r["Montant"])) if pd.notna(r["Montant"]) else 0) * 60,
            })
    return pd.DataFrame(pts)


def build_geo_arcs(df: pd.DataFrame) -> pd.DataFrame:
    """Arcs entre opérations suspectes d'un même client changeant de pays."""
    arcs = []
    geo = df[df["Suspecte"] & df["Explication"].str.contains("pays", case=False, na=False)]
    for client, grp in geo.groupby("Client"):
        grp = grp.sort_values("_dt", na_position="last")
        prev = None
        for _, r in grp.iterrows():
            code = str(r["Pays"]).strip().upper() if isinstance(r["Pays"], str) else None
            if code not in COUNTRY_COORDS:
                prev = None
                continue
            if prev is not None and prev["code"] != code:
                arcs.append({
                    "from_lon": prev["lon"], "from_lat": prev["lat"],
                    "to_lon": COUNTRY_COORDS[code][1], "to_lat": COUNTRY_COORDS[code][0],
                    "client": client,
                    "route": f"{prev['code']} → {code}",
                })
            prev = {"code": code,
                    "lat": COUNTRY_COORDS[code][0], "lon": COUNTRY_COORDS[code][1]}
    return pd.DataFrame(arcs)


# --------------------------------------------------------------------------- #
#  Composants visuels
# --------------------------------------------------------------------------- #
def _kpi(label: str, value, sub: str = "", color: str = "#EAecF7") -> str:
    return (
        f'<div class="kpi"><div class="label">{label}</div>'
        f'<div class="value" style="color:{color}">{value}</div>'
        f'<div class="sub">{sub}</div></div>'
    )


def _risk_gauge(value: float):
    import plotly.graph_objects as go
    color = C_SAFE if value < 30 else (C_WARN if value < 60 else C_DANGER)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": " %", "font": {"size": 34, "color": "#EAecF7"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#5A627F"},
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 30], "color": "rgba(61,214,140,0.18)"},
                {"range": [30, 60], "color": "rgba(255,176,32,0.18)"},
                {"range": [60, 100], "color": "rgba(255,77,109,0.20)"},
            ],
        },
    ))
    fig.update_layout(height=240, margin=dict(l=10, r=10, t=10, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", font_color="#AAB2CF")
    return fig


def _motifs_donut(df: pd.DataFrame):
    import plotly.express as px
    motifs = (df.loc[df["Suspecte"], "Explication"].value_counts()
              .rename_axis("Motif").reset_index(name="Nombre"))
    fig = px.pie(motifs, names="Motif", values="Nombre", hole=0.62,
                 color_discrete_sequence=px.colors.sequential.Plasma_r)
    fig.update_traces(textinfo="value", textfont_size=13,
                      marker=dict(line=dict(color="#0A0E1A", width=2)))
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", font_color="#C7CEE6",
                      legend=dict(font=dict(size=11), orientation="v",
                                  yanchor="middle", y=0.5, x=1.02))
    return fig


def _scatter_3d(df: pd.DataFrame):
    import plotly.express as px
    plot = df.copy()
    plot["_dt"] = pd.to_datetime(plot["Date"], errors="coerce", utc=True)
    plot = plot.sort_values("_dt", na_position="last").reset_index(drop=True)
    plot["Chronologie"] = range(1, len(plot) + 1)
    plot["MontantPlot"] = plot["Montant"].fillna(0.0)
    fig = px.scatter_3d(
        plot, x="Chronologie", y="MontantPlot", z="Risque",
        color="Statut",
        color_discrete_map={"Suspecte": C_DANGER, "Saine": C_SAFE},
        size=plot["MontantPlot"].abs().clip(lower=5) + 5,
        size_max=26, opacity=0.9,
        hover_name="Transaction",
        hover_data={"Client": True, "Pays": True, "Devise": True,
                    "Commerçant": True, "Explication": True,
                    "Chronologie": False, "MontantPlot": False},
    )
    fig.update_layout(
        height=520, margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)", font_color="#C7CEE6",
        legend=dict(orientation="h", yanchor="bottom", y=0.98, x=0.0),
        scene=dict(
            xaxis_title="Chronologie", yaxis_title="Montant", zaxis_title="Risque (%)",
            xaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="#1E2742",
                       color="#8B93B2"),
            yaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="#1E2742",
                       color="#8B93B2"),
            zaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="#1E2742",
                       color="#8B93B2"),
        ),
    )
    return fig


def _globe(df: pd.DataFrame):
    """Globe terrestre 3D (projection orthographique) : points + arcs géodésiques.

    La projection orthographique de Plotly affiche une vraie planète que l'on
    peut faire tourner à la souris. Les arcs suivent automatiquement les
    grands cercles (géodésiques), comme de vrais trajets sur le globe.
    """
    import plotly.graph_objects as go

    pts = build_map_points(df)
    arcs = build_geo_arcs(df)
    if pts.empty:
        return None

    fig = go.Figure()

    # Arcs des trajets impossibles (lignes géodésiques rouges).
    if not arcs.empty:
        lons, lats = [], []
        for _, a in arcs.iterrows():
            lons += [a["from_lon"], a["to_lon"], None]
            lats += [a["from_lat"], a["to_lat"], None]
        fig.add_trace(go.Scattergeo(
            lon=lons, lat=lats, mode="lines",
            line=dict(width=2.4, color=C_DANGER),
            opacity=0.85, hoverinfo="skip", name="Trajet impossible",
        ))

    def _sizes(frame):
        return (7 + (frame["montant"].abs() / 250.0).clip(upper=22)).tolist()

    safe = pts[pts["color"].apply(lambda c: c[0] != 255)]
    susp = pts[pts["color"].apply(lambda c: c[0] == 255)]

    if not safe.empty:
        fig.add_trace(go.Scattergeo(
            lon=safe["lon"], lat=safe["lat"], mode="markers",
            name="Saine",
            marker=dict(size=_sizes(safe), color=C_SAFE, opacity=0.75,
                        line=dict(width=0.5, color="rgba(255,255,255,0.4)")),
            text=safe.apply(lambda r: f"{r['tx']} · {r['client']} · {r['pays']}"
                                      f"<br>Risque {r['risque']}% · {r['montant']:.0f}",
                            axis=1),
            hoverinfo="text",
        ))
    if not susp.empty:
        fig.add_trace(go.Scattergeo(
            lon=susp["lon"], lat=susp["lat"], mode="markers",
            name="Suspecte",
            marker=dict(size=_sizes(susp), color=C_DANGER, opacity=0.95,
                        line=dict(width=0.8, color="#fff")),
            text=susp.apply(lambda r: f"{r['tx']} · {r['client']} · {r['pays']}"
                                      f"<br>Risque {r['risque']}% · {r['montant']:.0f}",
                            axis=1),
            hoverinfo="text",
        ))

    fig.update_geos(
        projection_type="orthographic",
        projection_rotation=dict(lon=12, lat=22, roll=0),
        showland=True, landcolor="#1B2138",
        showocean=True, oceancolor="#0A1326",
        showlakes=True, lakecolor="#0A1326",
        showcountries=True, countrycolor="rgba(160,170,210,0.20)",
        showcoastlines=True, coastlinecolor="rgba(180,190,230,0.30)",
        showframe=False, bgcolor="rgba(0,0,0,0)",
        lataxis_showgrid=True, lonaxis_showgrid=True,
        lataxis_gridcolor="rgba(255,255,255,0.05)",
        lonaxis_gridcolor="rgba(255,255,255,0.05)",
    )
    fig.update_layout(
        height=580, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", font_color="#C7CEE6",
        legend=dict(orientation="h", yanchor="bottom", y=0.0, x=0.0,
                    bgcolor="rgba(0,0,0,0)"),
        geo=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


# --------------------------------------------------------------------------- #
#  Écran principal
# --------------------------------------------------------------------------- #
def render_interface(transactions: list[dict], results: list[dict]) -> None:
    """Tableau de bord intuitif pour le jury et un public non technique."""
    st.markdown(CSS, unsafe_allow_html=True)

    df = build_dataframe(transactions, results)
    total = len(df)
    alerts = int(df["Suspecte"].sum()) if total else 0
    clean = total - alerts
    clients_risque = df.loc[df["Suspecte"], "Client"].nunique() if total else 0
    taux = (alerts / total * 100) if total else 0.0
    risque_moyen = float(df.loc[df["Suspecte"], "Risque"].mean()) if alerts else 0.0

    niveau = ("Faible", C_SAFE) if taux < 15 else \
             (("Modéré", C_WARN) if taux < 40 else ("Élevé", C_DANGER))

    # --- Hero ---
    st.markdown(
        f"""
        <div class="hero">
          <h1>🛡️ Sentinelle anti-fraude</h1>
          <p>Analyse intelligente des transactions — détecter, prévenir et
          expliquer la fraude financière. <span class="badge {'danger' if alerts else 'safe'}">
          Niveau de risque global : {niveau[0]}</span></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- KPIs ---
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(_kpi("Transactions", total, "analysées dans ce lot"),
                unsafe_allow_html=True)
    k2.markdown(_kpi("Alertes", alerts, f"{taux:.0f}% du volume",
                     color=C_DANGER if alerts else C_SAFE), unsafe_allow_html=True)
    k3.markdown(_kpi("Transactions saines", clean, "aucune anomalie détectée",
                     color=C_SAFE), unsafe_allow_html=True)
    k4.markdown(_kpi("Clients à surveiller", clients_risque,
                     "au moins une alerte", color=C_ACCENT2),
                unsafe_allow_html=True)

    st.write("")

    # --- Jauge + Donut ---
    g1, g2 = st.columns([1, 1.3])
    with g1:
        st.markdown('<div class="section-title">Indice de risque du portefeuille</div>'
                    '<div class="section-sub">Risque moyen des transactions signalées</div>',
                    unsafe_allow_html=True)
        try:
            st.plotly_chart(_risk_gauge(risque_moyen), use_container_width=True,
                            config={"displayModeBar": False})
        except Exception as exc:  # noqa: BLE001
            st.info(f"Jauge indisponible ({exc}).")
    with g2:
        st.markdown('<div class="section-title">Pourquoi ces alertes ?</div>'
                    '<div class="section-sub">Répartition des motifs de signalement</div>',
                    unsafe_allow_html=True)
        if alerts:
            try:
                st.plotly_chart(_motifs_donut(df), use_container_width=True,
                                config={"displayModeBar": False})
            except Exception as exc:  # noqa: BLE001
                st.info(f"Graphique indisponible ({exc}).")
        else:
            st.success("Aucune alerte : toutes les transactions sont conformes.")

    st.divider()

    # --- Visualisation 3D ---
    st.markdown('<div class="section-title">Cartographie 3D des transactions</div>'
                '<div class="section-sub">Chronologie × Montant × Risque — '
                'faites pivoter la scène. Les points rouges sont suspects.</div>',
                unsafe_allow_html=True)
    try:
        st.plotly_chart(_scatter_3d(df), use_container_width=True,
                        config={"displayModeBar": False})
    except Exception as exc:  # noqa: BLE001
        st.info(f"Vue 3D indisponible ({exc}).")

    # --- Globe 3D des trajets ---
    arcs = build_geo_arcs(df)
    st.markdown('<div class="section-title">Planète 3D des trajets suspects</div>'
                '<div class="section-sub">Globe terrestre interactif (rotatif) — '
                'les arcs rouges = déplacements physiquement impossibles '
                '(carte clonée probable).</div>',
                unsafe_allow_html=True)
    try:
        globe = _globe(df)
        if globe is not None:
            st.plotly_chart(globe, use_container_width=True,
                            config={"displayModeBar": False})
            if not arcs.empty:
                st.caption("Trajets impossibles : " +
                           ", ".join(sorted(set(arcs["route"]))))
        else:
            st.info("Pas de coordonnées pays exploitables pour le globe.")
    except Exception as exc:  # noqa: BLE001
        st.info(f"Globe 3D indisponible ({exc}).")

    st.divider()

    # --- Top clients ---
    if alerts:
        top = (df.loc[df["Suspecte"] & df["Client"].notna()]
               .groupby("Client")
               .agg(Alertes=("Suspecte", "sum"), Risque_max=("Risque", "max"))
               .sort_values(["Alertes", "Risque_max"], ascending=False)
               .head(5).reset_index())
        st.markdown('<div class="section-title">Clients les plus à risque</div>',
                    unsafe_allow_html=True)
        st.dataframe(top, use_container_width=True, hide_index=True,
                     column_config={"Risque_max": st.column_config.ProgressColumn(
                         "Risque max", min_value=0, max_value=100, format="%d%%")})

    # --- Tableau filtrable ---
    st.markdown('<div class="section-title">Détail des transactions</div>',
                unsafe_allow_html=True)
    f1, f2, f3 = st.columns([1.2, 1.4, 1.4])
    with f1:
        vue = st.radio("Afficher", ["Seulement les suspectes", "Tout"],
                       index=0 if alerts else 1, horizontal=False)
    with f2:
        clients = ["(tous)"] + sorted(str(c) for c in df["Client"].dropna().unique())
        client_sel = st.selectbox("Filtrer par client", clients)
    with f3:
        motifs_list = ["(tous)"] + sorted(
            df.loc[df["Suspecte"], "Explication"].dropna().unique().tolist())
        motif_sel = st.selectbox("Filtrer par motif", motifs_list)

    view = df.copy()
    if vue == "Seulement les suspectes":
        view = view[view["Suspecte"]]
    if client_sel != "(tous)":
        view = view[view["Client"].astype(str) == client_sel]
    if motif_sel != "(tous)":
        view = view[view["Explication"] == motif_sel]

    show_cols = ["Transaction", "Client", "Date", "Montant", "Devise",
                 "Commerçant", "Pays", "Risque", "Suspecte", "Explication"]

    def _style(row):
        c = "background-color: rgba(255,77,109,0.14)" if row["Suspecte"] else ""
        return [c] * len(row)

    if view.empty:
        st.info("Aucune transaction ne correspond à ce filtre.")
    else:
        st.dataframe(
            view[show_cols].style.apply(_style, axis=1).format({"Montant": "{:.2f}"}),
            use_container_width=True, hide_index=True,
            column_config={"Risque": st.column_config.ProgressColumn(
                "Niveau de risque", min_value=0, max_value=100, format="%d%%")},
        )

    suspects = df[df["Suspecte"]]
    if not suspects.empty:
        st.download_button(
            "⬇️ Exporter les alertes (CSV)",
            data=suspects[show_cols].to_csv(index=False).encode("utf-8-sig"),
            file_name="alertes_fraude.csv", mime="text/csv")

    # --- Pédagogie ---
    with st.expander("🧠 Comment l'outil décide-t-il ?"):
        st.markdown(
            """
Chaque transaction est comparée à **l'historique du client** et passée au crible
de plusieurs règles, de la plus simple à la plus fine :

- **Champ obligatoire manquant** (pays, montant, commerçant…) → donnée douteuse.
- **Montant nul ou négatif** → opération anormale.
- **Montant très supérieur à l'habitude du client** → achat inhabituel à vérifier.
- **Deux pays différents en trop peu de temps** → déplacement impossible (carte clonée).
- **Rafale de transactions** en quelques minutes → test de carte volée.
- **Doublon / rejeu** (même montant et commerçant) → double débit suspect.

Pour **éviter de gêner les clients honnêtes**, un achat un peu plus cher que
d'ordinaire, ou un voyage avec assez de temps entre deux pays, **n'est pas** signalé.
            """
        )


def main() -> None:
    st.set_page_config(page_title="Sentinelle anti-fraude — INTELO2026",
                       page_icon="🛡️", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### 🛡️ Sentinelle")
        st.caption("Hackathon INTELO2026 · démo jury")
        st.divider()
        st.markdown("#### Données")
        use_sample = st.toggle("Fichier d'exemple", value=True)
        transactions: list[dict] = []
        if use_sample:
            transactions = load_transactions(str(SAMPLE_CSV))
            st.success(f"{len(transactions)} transactions chargées")
        else:
            uploaded = st.file_uploader("Importer un CSV", type=["csv"])
            if uploaded:
                tmp = Path(".streamlit_upload.csv")
                tmp.write_bytes(uploaded.getvalue())
                transactions = load_transactions(str(tmp))
                tmp.unlink(missing_ok=True)
                st.success(f"{len(transactions)} transactions importées")
        st.divider()
        st.caption("Astuce : faites pivoter la vue 3D à la souris pour "
                   "explorer montant et risque.")

    if not transactions:
        st.markdown(CSS, unsafe_allow_html=True)
        st.info("Chargez des transactions dans la barre latérale pour lancer l'analyse.")
        return

    try:
        results = detect_fraud(transactions)
    except NotImplementedError:
        st.error("Implémentez d'abord `detect_fraud` dans `fraud_detection.py`.")
        return
    except Exception as exc:  # noqa: BLE001
        st.error(f"Erreur lors de l'analyse : {exc}")
        return

    render_interface(transactions, results)


if __name__ == "__main__":
    main()
