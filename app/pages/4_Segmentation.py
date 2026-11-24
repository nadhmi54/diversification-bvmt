import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import commun as c

c.page("Segmentation (k-means)", "k-means++ avec 50 initialisations et la graine 42 ; features standardisées")

with st.sidebar:
    st.subheader("Réglages")
    esp = st.selectbox("Espace", list(c.ESPACES), format_func=c.ESPACES.get)
    liq = st.toggle("Titres liquides seulement (57)", value=False)

tab, votes, k_ret = c.criteres_k(esp, liq)
with st.sidebar:
    k = st.slider("Nombre de groupes k", 2, 10, k_ret, help=f"k retenu par le vote des 4 critères : {k_ret}")
projet = k == k_ret
(st.success if projet else st.warning)(
    f"k = {k} : valeur retenue par le vote des critères." if projet else f"Exploration : le vote des critères retient k = {k_ret}, vous regardez k = {k}.")

# ---- choix de k
st.subheader("Choix de k : 4 critères votent (plage testée 3 à 8)")
cols = st.columns(4)
for col, (crit, v) in zip(cols, votes.items()):
    col.metric(crit, f"k = {v}")
fig = make_subplots(rows=1, cols=4, subplot_titles=["Coude (inertie)", "Silhouette ↑", "Calinski-Harabasz ↑", "Davies-Bouldin ↓"])
for j, (cle, crit) in enumerate([("inertie", "Coude"), ("silhouette", "Silhouette"), ("calinski_harabasz", "Calinski-Harabasz"), ("davies_bouldin", "Davies-Bouldin")], 1):
    fig.add_trace(go.Scatter(x=tab.index, y=tab[cle], mode="lines+markers", line=dict(color=c.NAVY), showlegend=False,
                             marker=dict(color=[c.NAVY if d else c.GRIS for d in tab.dans_la_plage])), 1, j)
    fig.add_trace(go.Scatter(x=[votes[crit]], y=[tab.loc[votes[crit], cle]], mode="markers", showlegend=False,
                             marker=dict(symbol="star", size=18, color="gold", line=dict(color="black", width=1))), 1, j)
    fig.add_vline(x=k, line_dash="dash", line_color=c.ROUGE, row=1, col=j)
    fig.add_vrect(x0=2.5, x1=8.5, fillcolor=c.NAVY, opacity=0.04, line_width=0, row=1, col=j)
fig.update_layout(height=300, margin=dict(t=40, b=10))
st.plotly_chart(fig, width="stretch")
st.caption("Étoile : meilleur k de chaque critère (dans la plage 3-8). Trait rouge : k affiché. Points gris : k = 2, 9, 10, calculés en contrôle hors plage.")
sil = tab.loc[k, "silhouette"]
c.note(f"Silhouette à k = {k} : <b>{c.num(sil, 3)}</b>. "
       + ("En dessous de 0,5, les groupes sont <b>peu séparés</b> : c'est le cas partout à la BVMT." if sil < 0.5 else "Au-dessus de 0,5 : structure nette.")
       + (" Dans le plan rendement-volatilité, les critères s'améliorent presque à chaque k ajouté : c'est un nuage continu, sans groupes naturels." if esp == "RV" else ""))

# ---- carte des groupes
cl = c.clusters(esp, liq, k); i = c.info().loc[cl.index]; F = c.features().loc[cl.index]
plan, (ax1, ax2) = c.plan_affichage(esp, liq)
s = c.scores_if(esp, liq); sig = c.signales(s, 0.05)
st.subheader(f"Les {k} groupes")
d = plan.join(cl).join(i[["nom", "liquide"]]).join(F[["rendement_annualise", "volatilite_annualisee", "beta"]]).reset_index()
d["groupe"] = "cluster " + d.cluster.astype(str)
d["anomalie IF 5 %"] = sig
fig = px.scatter(d, x="axe 1", y="axe 2", color="groupe", symbol=d.liquide.map({True: "liquide", False: "peu liquide"}),
                 symbol_map={"liquide": "circle", "peu liquide": "x"}, color_discrete_sequence=c.PALETTE,
                 category_orders={"groupe": [f"cluster {j}" for j in range(1, k + 1)]},
                 hover_name="ticker", hover_data={"nom": True, "rendement_annualise": ":.1%", "volatilite_annualisee": ":.1%", "beta": ":.2f",
                                                   "axe 1": False, "axe 2": False, "groupe": True},
                 labels={"axe 1": ax1, "axe 2": ax2, "symbol": ""})
fig.update_traces(marker=dict(size=10))
an = d[d["anomalie IF 5 %"]]
fig.add_trace(go.Scatter(x=an["axe 1"], y=an["axe 2"], mode="markers+text", text=an.ticker, textposition="top right",
                         marker=dict(size=22, color="rgba(0,0,0,0)", line=dict(color="black", width=1.5)), name="anomalie IF à 5 %", hoverinfo="skip"))
fig.update_layout(height=540, margin=dict(t=10, b=10))
st.plotly_chart(fig, width="stretch")
if esp != "RV":
    st.caption("Affichage dans le plan des deux premières composantes principales de l'espace choisi ; le clustering, lui, utilise toutes les dimensions.")

# ---- profil des groupes
st.subheader("Profil de chaque groupe (médianes)")
lignes = []
for j in sorted(cl.unique()):
    t = cl.index[cl == j]
    lignes.append({"groupe": f"cluster {j}", "taille": len(t), "rendement": F.loc[t, "rendement_annualise"].median(),
                   "volatilité": F.loc[t, "volatilite_annualisee"].median(), "bêta": F.loc[t, "beta"].median(),
                   "séances échangées": i.loc[t, "part_seances_echangees"].median(),
                   "capitaux médians (TND)": i.loc[t, "capitaux_median_2023_2025"].median(),
                   "peu liquides": int((~i.loc[t, "liquide"]).sum()), "titres": ", ".join(sorted(t))})
P = pd.DataFrame(lignes)
st.dataframe(P, hide_index=True, width="stretch", column_config={
    "rendement": st.column_config.NumberColumn(format="%.3f"), "volatilité": st.column_config.NumberColumn(format="%.3f"),
    "bêta": st.column_config.NumberColumn(format="%.2f"), "séances échangées": st.column_config.NumberColumn(format="%.2f"),
    "capitaux médians (TND)": st.column_config.NumberColumn(format="%.0f"), "titres": st.column_config.TextColumn(width="large")})
if projet and esp in ("7F", "5F", "ACP") and not liq:
    c.note("<b>Lecture</b> : le grand groupe réunit les titres liquides et liés au marché (dont les banques sauf BTE), le second les titres "
           "volatils, à rendement proche de zéro et peu liés au marché, avec des capitaux échangés environ 120 fois plus petits. "
           "PLTU forme un groupe à elle seule. <b>Les groupes reflètent la liquidité et la sensibilité au marché, pas les secteurs.</b>")

with st.expander("Tableau complet des critères"):
    st.dataframe(tab.round(3), width="stretch")
