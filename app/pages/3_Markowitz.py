import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import commun as c

c.page("Markowitz", "Sans vente à découvert : poids entre 0 et 1, somme égale à 1")

RF_PROJET = c.taux_sans_risque()["taux_continu_annuel_utilise"]
with st.sidebar:
    st.subheader("Réglages")
    liq = st.toggle("Titres liquides seulement (57)", value=False)
    rf_simple = st.slider("Taux sans risque annuel (%)", 0.0, 12.0, 7.0, 0.25,
                          help="7 % = TMM d'octobre 2026 ; converti en taux continu ln(1 + taux)")
rf = float(np.log(1 + rf_simple / 100))
projet = (not liq) and abs(rf - RF_PROJET) < 1e-6
if projet:
    st.success("Réglages du projet : 75 titres, taux sans risque 7 % (6,77 % en continu). Mêmes résultats que la S3.")
else:
    st.warning("Exploration : les réglages diffèrent de ceux du projet.")

m = c.markowitz(liq, rf)
F = c.features().loc[m["tickers"]]; i = c.info().loc[m["tickers"]]

col = st.columns(4)
col[0].metric("Sharpe maximal", c.num(m["perf_ms"][2]), help="(rendement − taux sans risque) / volatilité")
col[1].metric("Rendement / volatilité", f"{c.pct(m['perf_ms'][0])} / {c.pct(m['perf_ms'][1])}")
col[2].metric("Variance minimale : volatilité", c.pct(m["perf_gmv"][1]), help=f"rendement {c.pct(m['perf_gmv'][0])}")
col[3].metric("Meilleur aléatoire", c.num(m["sharpe_alea_max"]), help="Meilleur Sharpe parmi 20 000 portefeuilles tirés au hasard")

fig = go.Figure()
for liquide, nom, sym, coul in [(True, "titres liquides", "circle", c.BLEU), (False, "titres peu liquides", "x", c.ROUGE)]:
    t = i.index[i.liquide == liquide]
    if len(t):
        fig.add_trace(go.Scatter(x=F.loc[t, "volatilite_annualisee"], y=F.loc[t, "rendement_annualise"], mode="markers", name=f"{nom} ({len(t)})",
                                 marker=dict(symbol=sym, size=8, color=coul, opacity=0.8), text=[f"{x} — {i.loc[x, 'nom']}" for x in t],
                                 hovertemplate="%{text}<br>volatilité %{x:.1%}<br>rendement %{y:.1%}<extra></extra>"))
fr = m["front"]
fig.add_trace(go.Scatter(x=fr.volatilite, y=fr.rendement, mode="lines", name="frontière efficiente", line=dict(color="black", width=2.5),
                         customdata=fr.sharpe, hovertemplate="volatilité %{x:.1%}<br>rendement %{y:.1%}<br>Sharpe %{customdata:.2f}<extra></extra>"))
x = np.linspace(0, m["perf_ms"][1] * 1.8, 20)
fig.add_trace(go.Scatter(x=x, y=rf + m["perf_ms"][2] * x, mode="lines", name="droite de marché des capitaux", line=dict(color=c.ORANGE, dash="dash")))
for (r, v, s), nom, sym, coul in [(m["perf_ms"], "Sharpe maximal", "star", "gold"), (m["perf_gmv"], "variance minimale", "diamond", "green"),
                                  (m["perf_1n"], "1/N", "square", c.GRIS)]:
    fig.add_trace(go.Scatter(x=[v], y=[r], mode="markers", name=f"{nom} (Sharpe {c.num(s)})", marker=dict(symbol=sym, size=16, color=coul, line=dict(color="black", width=1))))
fig.add_hline(y=rf, line_dash="dot", line_color=c.GRIS, annotation_text=f"taux sans risque {c.pct(rf, 2)}")
fig.update_layout(height=560, xaxis_title="Volatilité annualisée", yaxis_title="Rendement annualisé (log)",
                  xaxis_tickformat=".0%", yaxis_tickformat=".0%", margin=dict(t=10, b=10), legend=dict(x=0.01, y=0.01, bgcolor="rgba(255,255,255,0.8)"))
st.plotly_chart(fig, width="stretch")

with st.expander("Comment la courbe est construite"):
    st.markdown(f"""
1. **Ingrédients** : μ (rendement moyen × 252) et Σ (covariance × 252) des rendements log journaliers.
2. **Variance minimale** (losange vert) : le portefeuille le moins risqué, sans viser de rendement.
3. **Point d'arrivée** : le titre au plus haut rendement, avec 100 % du capital dessus.
4. **Entre les deux** : 40 rendements cibles ; pour chacun, on minimise wᵀΣw sous Σw = 1, μᵀw = cible, w ≥ 0 (optimisation quadratique exacte, SLSQP).
5. **Sharpe maximal** (étoile) : maximum exact de (rendement − r_f) / volatilité, par le changement de variable de Cornuejols-Tütüncü.
6. **Droite orange** : part du taux sans risque et touche la courbe à l'étoile ; sa pente est le Sharpe maximal.
7. **Contrôles** : 1/N (carré gris) et 20 000 portefeuilles aléatoires, tous moins bons.
""")

a, b = st.columns(2)
for col, cle, titre in [(a, "ms", "Poids du portefeuille de Sharpe maximal"), (b, "gmv", "Poids du portefeuille de variance minimale")]:
    with col:
        st.subheader(titre)
        w = m[cle][m[cle] > 0.005].sort_values(ascending=True)
        d = w.rename("poids").to_frame().join(i[["nom", "liquide"]]).rename_axis("ticker").reset_index()
        fig = px.bar(d, x="poids", y="ticker", orientation="h", color=d.liquide.map({True: "liquide", False: "peu liquide"}),
                     color_discrete_map={"liquide": c.NAVY, "peu liquide": c.ORANGE}, hover_data=["nom"], labels={"ticker": "", "color": ""})
        fig.update_yaxes(categoryorder="array", categoryarray=list(d.ticker))
        fig.update_layout(height=max(300, 22 * len(d)), xaxis_tickformat=".0%", margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.05))
        st.plotly_chart(fig, width="stretch")
        st.caption(f"{len(w)} titres avec un poids supérieur à 0,5 %.")

if not liq:
    c.note("<b>Le piège de la variance minimale</b> : elle met environ 37 % sur PLTU, échangée 4 % des séances. Son prix ne bouge presque jamais, "
           "donc sa volatilité calculée est faussement faible. Activez « Titres liquides seulement » : la volatilité minimale passe de 2,9 % à 4,8 %.", alerte=True)
c.note("<b>Pourquoi le Sharpe est si élevé</b> : μ et Σ sont estimés sur les mêmes données que l'optimisation (dans l'échantillon), "
       "sur un marché très haussier. Ce n'est pas une performance réalisable ; le test hors échantillon est la prochaine étape.")
