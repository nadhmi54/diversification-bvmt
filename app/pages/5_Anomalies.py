import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import commun as c

c.page("Anomalies (Isolation Forest)", "500 arbres, graine 42 : un titre anormal s'isole en peu de découpes aléatoires")

with st.sidebar:
    st.subheader("Réglages")
    esp = st.selectbox("Espace", list(c.ESPACES), format_func=c.ESPACES.get, index=0)
    liq = st.toggle("Titres liquides seulement (57)", value=False)
    taux = st.select_slider("Taux de contamination", options=[0.03, 0.05, 0.08, 0.10], value=0.05, format_func=lambda x: c.pct(x, 0))
(st.success if taux == 0.05 else st.warning)("Taux du projet : 5 %, comme l'article." if taux == 0.05 else f"Exploration : taux de {c.pct(taux, 0)} (le projet retient 5 %).")

s = c.scores_if(esp, liq).sort_values(ascending=False); sig = pd.Series(c.signales(s, taux), index=s.index)
i = c.info().loc[s.index]
st.subheader(f"Scores d'anomalie — {c.ESPACES[esp]}")
d = s.rename("score").to_frame().join(i[["nom", "liquide"]]).reset_index()
d["statut"] = ["signalé" if sig[t] else ("peu liquide" if not i.loc[t, "liquide"] else "normal") for t in d.ticker]
fig = px.bar(d, x="ticker", y="score", color="statut", color_discrete_map={"signalé": c.ROUGE, "normal": c.NAVY, "peu liquide": c.ORANGE},
             hover_data=["nom"], labels={"ticker": "", "score": "score d'anomalie (plus haut = plus anormal)", "statut": ""})
for t_, ls in zip(c.TAUX_IF, ["dot", "dash", "dashdot", "solid"]):
    fig.add_vline(x=int(-(-t_ * len(s) // 1)) - 0.5, line_dash=ls, line_color=c.GRIS)
fig.update_xaxes(categoryorder="array", categoryarray=list(s.index))
fig.update_layout(height=400, margin=dict(t=30, b=10), legend=dict(orientation="h", y=1.12), yaxis_range=[s.min() * 0.95, s.max() * 1.03])
st.plotly_chart(fig, width="stretch")
st.caption("Lignes grises verticales : seuils à 3, 5, 8 et 10 %. Le taux ne change pas les scores, seulement le seuil : à 5 %, les 4 titres de plus haut score sont signalés (3 pour 57 titres).")

st.subheader("Titres signalés et nature de l'anomalie")
Z = c.z_features(liq, c.F5 if esp == "5F" else c.F7)
lignes = []
for t in s.index[sig.values]:
    n, j = c.nature(t, Z)
    lignes.append({"ticker": t, "nom": i.loc[t, "nom"], "score": s[t], "nature": n, "justification": j,
                   "rendement": c.features().loc[t, "rendement_annualise"]})
st.dataframe(pd.DataFrame(lignes), hide_index=True, width="stretch",
             column_config={"score": st.column_config.NumberColumn(format="%.3f"), "rendement": st.column_config.NumberColumn(format="%.3f"),
                            "justification": st.column_config.TextColumn(width="large")})
c.note("Règle : <b>artefact d'illiquidité</b> si le titre est échangé moins de 60 % des séances ou a plus de 50 % de rendements nuls ; "
       "sinon <b>performance extrême</b> si une feature est à plus de 2 écarts-types ; sinon <b>atypique modéré</b>. "
       "Aucune anomalie n'est présentée comme une société en difficulté : il faudrait une preuve externe.")

st.subheader("Stabilité : combien de fois chaque titre est signalé ?")
st.caption("S4 : 3 espaces (RV, 7F, ACP) × 4 taux = 12 tests ; un titre est une anomalie stable s'il est signalé au moins 8 fois sur 12.")
nb = c.stabilite_anomalies(liq); nb = nb[nb > 0].sort_values()
d = nb.rename("signalements").to_frame().join(c.info()[["nom", "liquide"]]).reset_index()
fig = px.bar(d, x="signalements", y="ticker", orientation="h", color=d.liquide.map({True: "titre liquide", False: "illiquidité"}),
             color_discrete_map={"illiquidité": c.NAVY, "titre liquide": c.ORANGE}, hover_data=["nom"], text="signalements",
             labels={"ticker": "", "color": ""})
fig.update_yaxes(categoryorder="array", categoryarray=list(d.ticker))
fig.add_vline(x=8, line_dash="dash", line_color=c.ROUGE, annotation_text="stable (≥ 8)")
fig.update_layout(height=max(320, 26 * len(d)), xaxis_range=[0, 12.5], margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.06))
st.plotly_chart(fig, width="stretch")
if not liq:
    c.note("<b>Lecture</b> : PLTU (12/12), SIMPA (11) et SOTET (10) sont stables. PLTU, SIMPA et BHASS sont des titres presque jamais échangés : "
           "leur prix figé les rend « anormaux ». SOTET (59 %) et AB (47 %) sont de vrais extrêmes de performance. "
           "<b>La plupart des anomalies viennent de l'illiquidité</b>, ce que l'article ne vérifiait pas.")
else:
    c.note("Sur les 57 titres liquides, les anomalies stables sont <b>AB, SOTET et WIFAK</b> (S4, 7 features) ; "
           "avec 5 features (S4b), AB, CELL et SOTET.")
