import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import commun as c

c.page("Fiche titre", "Tout ce que le projet dit d'un titre, sur une page")

i = c.info(); F = c.features()
t = st.selectbox("Titre", list(i.index), index=list(i.index).index("SOTET"), format_func=lambda x: f"{x} — {i.loc[x, 'nom']}")
r = i.loc[t]; f = F.loc[t]

col = st.columns(5)
col[0].metric("Rendement annualisé", c.pct(f.rendement_annualise))
col[1].metric("Volatilité annualisée", c.pct(f.volatilite_annualisee))
col[2].metric("Bêta", c.num(f.beta))
col[3].metric("Séances échangées", c.pct(r.part_seances_echangees, 0))
col[4].metric("Liquidité", "liquide" if r.liquide else "peu liquide")

a, b = st.columns([3, 2])
with a:
    st.subheader("Position par rapport aux 75 titres")
    Z = c.z_features(False)
    z = Z.loc[t].rename(c.LIB)
    fig = go.Figure(go.Bar(x=z.values, y=z.index, orientation="h", marker_color=[c.ROUGE if abs(v) > 2 else c.NAVY for v in z.values],
                           text=[f"{v:+.1f}σ" for v in z.values], textposition="outside"))
    fig.add_vline(x=0, line_color="black"); fig.add_vrect(x0=-2, x1=2, fillcolor=c.NAVY, opacity=0.06, line_width=0)
    fig.update_layout(height=340, margin=dict(t=10, b=10), xaxis_title="écart à la moyenne, en écarts-types (rouge : au-delà de 2σ)")
    st.plotly_chart(fig, width="stretch")
with b:
    st.subheader("Valeurs des 7 features")
    st.dataframe(f.rename(c.LIB).to_frame("valeur").round(4), width="stretch")

st.subheader("Segmentation et anomalies")
lignes = []
for e in c.ESPACES:
    k = c.criteres_k(e, False)[2]; cl = c.clusters(e, False, k)
    s = c.scores_if(e, False); rang = int((s > s[t]).sum()) + 1
    lignes.append({"espace": c.ESPACES[e], "k": k, "groupe": f"cluster {cl[t]} (sur {k})", "taille du groupe": int((cl == cl[t]).sum()),
                   "rang IF (1 = plus anormal)": f"{rang} / {len(s)}", "signalé à 5 %": "oui" if c.signales(s, 0.05)[list(s.index).index(t)] else "non"})
st.dataframe(pd.DataFrame(lignes), hide_index=True, width="stretch")
nb = int(c.stabilite_anomalies(False)[t])
n, j = c.nature(t, c.z_features(False))
if nb >= 8:
    c.note(f"<b>Anomalie stable</b> : signalé {nb} fois sur 12 en S4. Nature : <b>{n}</b> — {j}.", alerte=True)
elif nb > 0:
    c.note(f"Signalé {nb} fois sur 12 en S4 (pas assez pour être une anomalie stable). Si on le classait : {n.lower()} — {j}.")
else:
    c.note("Jamais signalé par Isolation Forest dans les 12 tests de la S4.")

m = c.markowitz(False, c.taux_sans_risque()["taux_continu_annuel_utilise"])
st.caption(f"Poids dans le portefeuille de Sharpe maximal : {c.pct(m['ms'][t])} · dans la variance minimale : {c.pct(m['gmv'][t])}.")

st.subheader("Cours")
x = c.cotations(); x = x[x.ticker == t].sort_values("date")
fig = go.Figure()
fig.add_trace(go.Scatter(x=x.date, y=x.cloture, name="clôture brute", line=dict(color=c.GRIS, width=1.2)))
fig.add_trace(go.Scatter(x=x.date, y=x.cloture_ajustee, name="cours ajusté", line=dict(color=c.NAVY, width=2)))
for d in x.date[(x.facteur - 1).abs() > 1e-9]:
    fig.add_vline(x=d, line_dash="dot", line_color=c.ORANGE)
fig.update_layout(height=380, margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.08), yaxis_title="TND")
st.plotly_chart(fig, width="stretch")
st.caption("Traits orange : opérations sur titres (dividendes, attributions gratuites, divisions), neutralisées par le cours de référence.")
