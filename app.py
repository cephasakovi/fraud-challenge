"""
Interface Streamlit — À CRÉER PAR VOUS pour le jury.

Le jury lancera :  streamlit run app.py

Règles :
  - Ne modifiez pas l'appel à detect_fraud / load_transactions (contrat technique).
  - Personnalisez render_interface() : clarté, intuitivité, compréhension pour un public non technique.
  - L'interface n'est PAS notée par la CI ; elle sert au jury pour repêcher et comparer les candidats.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from fraud_detection import detect_fraud, load_transactions

SAMPLE_CSV = Path(__file__).parent / "data" / "sample_transactions.csv"


def render_interface(transactions: list[dict], results: list[dict]) -> None:
    """
    ══════════════════════════════════════════════════════════════════
    À COMPLÉTER — votre interface intuitive pour le jury / le public.
    ══════════════════════════════════════════════════════════════════

    Idées (libres) :
      - titres et textes en langage simple (« transaction suspecte », « client à risque ») ;
      - cartes / indicateurs visuels (nombre d'alertes, niveau de risque) ;
      - tableau ou liste filtrable (uniquement les suspectes, par client, par pays…) ;
      - codes couleur, icônes, graphiques ;
      - zone « comment l'IA / vos règles décident » pour expliquer une alerte.

    Le jury évalue : clarté, utilité, intuitivité — pas le code en lui-même.
    """
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

    total = len(df)
    alerts = int(df["Suspecte"].sum()) if total else 0
    clean = total - alerts
    clients_risque = (
        df.loc[df["Suspecte"], "Client"].nunique() if total else 0
    )
    taux = (alerts / total * 100) if total else 0.0

    # --- Indicateurs clés (langage simple) ---
    st.subheader("Vue d'ensemble")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Transactions analysées", total)
    c2.metric("Alertes (suspectes)", alerts, delta=f"{taux:.0f}% du volume",
              delta_color="inverse")
    c3.metric("Transactions saines", clean)
    c4.metric("Clients à surveiller", clients_risque)

    if alerts:
        st.error(f"⚠️ {alerts} transaction(s) suspecte(s) à vérifier en priorité.")
    else:
        st.success("✅ Aucune transaction suspecte détectée sur ce lot.")

    st.divider()

    # --- Pourquoi ces alertes ? (répartition par motif) ---
    if alerts:
        st.subheader("Pourquoi ces alertes ?")
        motifs = (
            df.loc[df["Suspecte"], "Explication"]
            .value_counts()
            .rename_axis("Motif")
            .reset_index(name="Nombre")
        )
        cg, ct = st.columns([1, 1])
        with cg:
            st.caption("Répartition par motif")
            st.bar_chart(motifs.set_index("Motif"))
        with ct:
            pays = (
                df.loc[df["Suspecte"] & df["Pays"].notna(), "Pays"]
                .value_counts()
                .rename_axis("Pays")
                .reset_index(name="Alertes")
            )
            if not pays.empty:
                st.caption("Alertes par pays")
                st.bar_chart(pays.set_index("Pays"))
            else:
                st.dataframe(motifs, use_container_width=True, hide_index=True)

    st.divider()

    # --- Tableau filtrable ---
    st.subheader("Détail des transactions")
    f1, f2 = st.columns([1, 2])
    with f1:
        vue = st.radio(
            "Afficher",
            ["Seulement les suspectes", "Tout"],
            index=0 if alerts else 1,
            horizontal=False,
        )
    with f2:
        clients = ["(tous)"] + sorted(
            str(c) for c in df["Client"].dropna().unique()
        )
        client_sel = st.selectbox("Filtrer par client", clients)

    view = df.copy()
    if vue == "Seulement les suspectes":
        view = view[view["Suspecte"]]
    if client_sel != "(tous)":
        view = view[view["Client"].astype(str) == client_sel]

    def _style(row):
        color = "background-color: rgba(255,75,75,0.18)" if row["Suspecte"] else ""
        return [color] * len(row)

    if view.empty:
        st.info("Aucune transaction ne correspond à ce filtre.")
    else:
        st.dataframe(
            view.style.apply(_style, axis=1).format({"Montant": "{:.2f}"}),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Risque": st.column_config.ProgressColumn(
                    "Niveau de risque",
                    min_value=0, max_value=100, format="%d%%",
                ),
            },
        )

    # --- Export des alertes pour l'équipe conformité ---
    suspects = df[df["Suspecte"]]
    if not suspects.empty:
        st.download_button(
            "⬇️ Exporter les alertes (CSV)",
            data=suspects.to_csv(index=False).encode("utf-8-sig"),
            file_name="alertes_fraude.csv",
            mime="text/csv",
        )

    # --- Zone pédagogique : comment l'outil décide ---
    with st.expander("Comment l'outil décide-t-il ?"):
        st.markdown(
            """
Chaque transaction est comparée à **l'historique du client** et passée au crible
de plusieurs règles, de la plus simple à la plus fine :

- **Champ obligatoire manquant** (pays, montant, commerçant…) → donnée douteuse.
- **Montant nul ou négatif** → opération anormale.
- **Montant très supérieur à l'habitude du client** (plusieurs fois sa dépense
  habituelle) → achat inhabituel à vérifier.
- **Deux pays différents en trop peu de temps** → déplacement physiquement
  impossible (carte clonée probable).
- **Rafale de transactions** en quelques minutes → test de carte volée.

Pour **éviter de gêner les clients honnêtes**, une transaction simplement un peu
plus chère que d'ordinaire, ou un voyage avec assez de temps entre deux pays,
**n'est pas** signalée.
            """
        )


def main() -> None:
    st.set_page_config(
        page_title="Détection de fraude — Hackathon INTELO2026",
        page_icon="🛡️",
        layout="wide",
    )

    st.title("Détection de fraude financière")
    st.caption("Hackathon INTELO2026 — interface participant · évaluée par le jury")

    with st.sidebar:
        st.header("Charger des données")
        use_sample = st.toggle("Utiliser le fichier d'exemple", value=True)
        transactions: list[dict] = []

        if use_sample:
            transactions = load_transactions(str(SAMPLE_CSV))
            st.success(f"{len(transactions)} transactions (exemple)")
        else:
            uploaded = st.file_uploader("Importer un CSV", type=["csv"])
            if uploaded:
                tmp = Path(".streamlit_upload.csv")
                tmp.write_bytes(uploaded.getvalue())
                transactions = load_transactions(str(tmp))
                tmp.unlink(missing_ok=True)
                st.success(f"{len(transactions)} transactions importées")

        st.divider()
        st.markdown(
            "**Jury :** évaluez l'ergonomie et la clarté de l'écran principal, "
            "pas seulement le score des tests."
        )

    if not transactions:
        st.info("Chargez des transactions (barre latérale) puis lancez l'analyse.")
        return

    if st.button("Analyser", type="primary"):
        try:
            results = detect_fraud(transactions)
        except NotImplementedError:
            st.error("Implémentez d'abord `detect_fraud` dans `fraud_detection.py`.")
            return
        except Exception as exc:
            st.error(f"Erreur : {exc}")
            return

        render_interface(transactions, results)


if __name__ == "__main__":
    main()
