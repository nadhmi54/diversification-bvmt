import numpy as np
import plotly.express as px
import streamlit as st
import commun as c

c.page("Paramètres (features)", "Une valeur par titre sur toute la période, calculée sur les rendements log journaliers")

with st.expander("Définitions et formules", expanded=False):
    st.markdown("""
| Feature | Calcul | Ce qu'elle mesure |
|---|---|---|
| Rendement | moyenne des rendements log × 252 | le gain annuel moyen |
| Volatilité | écart-type × √252 | la dispersion des rendements |
| Skewness | 3ᵉ moment standardisé | l'asymétrie (gains ou pertes extrêmes) |
| Kurtosis | 4ᵉ moment standardisé − 3 | l'épaisseur des queues |
| VaR 95 % | quantile à 5 % des rendements journaliers | la perte d'un des 5 % pires jours |
| CVaR 95 % | moyenne des rendements sous la VaR | la perte moyenne de ces pires jours |
| Bêta | Cov(titre, Tunindex) / Var(Tunindex) | la sensibilité au marché |

Rendement journalier : r = ln(clôture / cours de référence).
""")

F = c.features(); i = c.info()
st.subheader("Tableau des 75 titres × 7 features")
t = F.rename(columns=c.LIB).join(i[["nom", "liquide"]]).reset_index()
st.dataframe(t[["ticker", "nom", "liquide"] + list(c.LIB.values())], hide_index=True, width="stretch",
             column_config={k: st.column_config.NumberColumn(format="%.3f") for k in c.LIB.values()})

st.subheader("Corrélations entre features")
meth = st.radio("Méthode", ["Pearson", "Spearman (rangs, moins sensible aux extrêmes)"], horizontal=True)
m = F.corr(method="pearson" if meth == "Pearson" else "spearman").rename(index=c.LIB, columns=c.LIB)
fig = px.imshow(m.round(2), text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto")
fig.update_layout(height=470, margin=dict(t=10, b=10))
st.plotly_chart(fig, width="stretch")
c.note("<b>Deux paires redondantes</b> : skewness / kurtosis (0,92) et VaR / CVaR (0,89 en Pearson). "
       "Les garder toutes les deux compte deux fois la même information dans les distances. "
       "La S4b retire le <b>kurtosis</b> (dominé par PLTU, 164) et la <b>VaR</b> (très liée à la volatilité, −0,91) : "
       "il reste <b>rendement, volatilité, skewness, CVaR et bêta</b>. La corrélation volatilité / CVaR (−0,85) est gardée "
       "volontairement : ce sont deux notions de risque différentes.")

st.subheader("Distribution d'une feature")
a, b = st.columns([1, 3])
with a:
    f = st.selectbox("Feature", list(c.LIB), format_func=c.LIB.get)
    st.caption("Les titres peu liquides sont en orange : ils se placent souvent aux extrêmes.")
with b:
    d = F[[f]].join(i[["nom", "liquide"]]).reset_index().sort_values(f)
    fig = px.bar(d, x="ticker", y=f, color=d.liquide.map({True: "liquide", False: "peu liquide"}),
                 color_discrete_map={"liquide": c.NAVY, "peu liquide": c.ORANGE}, hover_data=["nom"],
                 labels={f: c.LIB[f], "ticker": "", "color": ""})
    if f in ("rendement_annualise", "volatilite_annualisee"):
        fig.update_layout(yaxis_tickformat=".0%")
    fig.update_layout(height=380, margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.08))
    st.plotly_chart(fig, width="stretch")
