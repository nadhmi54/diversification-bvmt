import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import commun as c

c.page("Données", "Sources officielles de la Bourse de Tunis : archives annuelles 2023-2025 et bulletins officiels quotidiens 2026")

i = c.info()
col = st.columns(4)
col[0].metric("Titres", len(i))
col[1].metric("Liquides (≥ 60 % des séances)", int(i.liquide.sum()))
col[2].metric("Peu liquides", int((~i.liquide).sum()))
col[3].metric("Médiane des séances échangées", c.pct(i.part_seances_echangees.median(), 0))

st.subheader("Liquidité des 75 titres")
d = i.reset_index().sort_values("part_seances_echangees")
fig = px.bar(d, x="ticker", y="part_seances_echangees", color=d.liquide.map({True: "liquide", False: "peu liquide"}),
             color_discrete_map={"liquide": c.NAVY, "peu liquide": c.ORANGE},
             hover_data={"nom": True, "part_rendements_nuls": ":.0%", "part_seances_echangees": ":.0%"},
             labels={"part_seances_echangees": "Part des séances échangées", "ticker": "", "color": ""})
fig.add_hline(y=c.SEUIL_LIQUIDITE, line_dash="dash", line_color=c.ROUGE, annotation_text="seuil 60 %")
fig.update_layout(height=380, yaxis_tickformat=".0%", margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.08))
st.plotly_chart(fig, width="stretch")
c.note("Un titre peu liquide a beaucoup de jours sans transaction : son prix ne bouge pas, ses rendements sont nuls, "
       "et sa volatilité paraît faible. C'est la source de la plupart des « anomalies » des pages suivantes.")

st.subheader("Prix d'un titre : brut et corrigé des opérations sur titres")
cot = c.cotations()
choix = st.selectbox("Titre", list(i.index), index=list(i.index).index("BIAT"),
                     format_func=lambda t: f"{t} — {i.loc[t, 'nom']}")
x = cot[cot.ticker == choix].sort_values("date")
ost = x[(x.facteur - 1).abs() > 1e-9]
fig = go.Figure()
fig.add_trace(go.Scatter(x=x.date, y=x.cloture, name="cours de clôture brut", line=dict(color=c.GRIS, width=1.3)))
fig.add_trace(go.Scatter(x=x.date, y=x.cloture_ajustee, name="cours ajusté (base de nos calculs)", line=dict(color=c.NAVY, width=2)))
for _, r in ost.iterrows():
    fig.add_vline(x=r.date, line_dash="dot", line_color=c.ORANGE)
fig.update_layout(height=420, margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.08), yaxis_title="TND")
st.plotly_chart(fig, width="stretch")
if len(ost):
    t = ost[["date", "reference", "cloture", "facteur"]].copy()
    t["date"] = t.date.dt.strftime("%d/%m/%Y")
    t = t.rename(columns={"reference": "cours de référence", "cloture": "clôture du jour"})
    st.markdown(f"**{len(ost)} opération(s) sur titres détectée(s)** (traits orange). Le facteur = cours de référence du jour / clôture de la veille ; "
                "le rendement du jour est calculé depuis le cours de référence, ce qui neutralise la baisse mécanique.")
    st.dataframe(t, hide_index=True, width="stretch")
else:
    st.caption("Aucune opération sur titres sur la période pour ce titre.")
if choix == "BIAT":
    c.note("Exemple de la présentation : sans correction, l'attribution gratuite de BIAT faisait apparaître une fausse baisse de 10 % ; "
           "corrigée, c'est une vraie hausse de 2,4 %.")

st.subheader("Tableau des titres")
t = i.reset_index()[["ticker", "nom", "liquide", "part_seances_echangees", "part_rendements_nuls", "capitaux_median_2023_2025", "nb_ost"]]
st.dataframe(t, hide_index=True, width="stretch", column_config={
    "part_seances_echangees": st.column_config.ProgressColumn("Séances échangées", format="%.2f", min_value=0, max_value=1),
    "part_rendements_nuls": st.column_config.NumberColumn("Rendements nuls", format="%.2f"),
    "capitaux_median_2023_2025": st.column_config.NumberColumn("Capitaux médians 2023-2025 (TND)", format="%.0f"),
    "nb_ost": "Opérations sur titres"})
