import streamlit as st
import commun as c

c.page("Diversification non supervisée à la Bourse de Tunis",
       "Critique de Rebai et al. (2021) et réplication sur les données officielles de la BVMT, 2023-2026")

i = c.info()
col = st.columns(5)
col[0].metric("Séances", "960", help="Du 02/01/2023 au 03/11/2026")
col[1].metric("Titres analysés", f"{len(i)}", help="Sociétés encore cotées au 03/11/2026")
col[2].metric("Titres liquides", f"{int(i.liquide.sum())}", help="Échangés au moins 60 % des séances")
col[3].metric("Opérations sur titres corrigées", "228")
col[4].metric("Taux sans risque", "6,77 %", help="TMM d'octobre 2026 (7 %) en taux continu")

st.subheader("La question")
c.note("Peut-on <b>diversifier</b> un portefeuille à la Bourse de Tunis en <b>regroupant les actions qui se ressemblent</b> "
       "(k-means) et en <b>repérant les actions anormales</b> (Isolation Forest) ? L'article de Rebai et al. (2021) répond oui. "
       "Nous refaisons l'étude sur des données récentes et officielles, en vérifiant chaque choix.")

st.subheader("Les étapes")
etapes = [("1. Données", "Sources officielles BVMT, prix corrigés des opérations sur titres", "Données"),
          ("2. Paramètres", "7 features par titre ; version à 5 features sans redondance", "Paramètres"),
          ("3. Markowitz", "Variance minimale, Sharpe maximal, frontière efficiente", "Markowitz"),
          ("4. Segmentation", "k-means dans 4 espaces, choix de k par 4 critères", "Segmentation"),
          ("5. Anomalies", "Isolation Forest, stabilité, nature de chaque anomalie", "Anomalies")]
cols = st.columns(5)
for col, (t, d, _) in zip(cols, etapes):
    with col:
        st.markdown(f"**{t}**")
        st.caption(d)

st.subheader("Ce qu'il faut retenir")
a, b = st.columns(2)
with a:
    c.note("<b>Les groupes ne suivent pas les secteurs.</b> Avec 7 ou 5 features, k-means trouve 3 groupes : "
           "les titres liquides et liés au marché (dont les banques sauf BTE), les titres volatils et peu liés au marché, "
           "et PLTU seule. La structure reste faible (silhouette inférieure à 0,5).")
    c.note("<b>Le Sharpe de 4,93 n'est pas une performance réalisable</b> : il est calculé sur les mêmes données que l'optimisation, "
           "dans un marché très haussier. La variance minimale est piégée par PLTU, presque jamais échangée.")
with b:
    c.note("<b>La plupart des anomalies sont de l'illiquidité.</b> PLTU, SIMPA et BHASS sont signalées parce que leur prix "
           "ne bouge presque jamais. SOTET et AB sont de vrais extrêmes de performance, à confirmer avec des sources externes. "
           "Aucune anomalie n'est présentée comme une société en difficulté.")
    c.note("<b>Prochaine étape</b> : construire un portefeuille « un titre par cluster » et le comparer au 1/N et à Markowitz "
           "<b>hors échantillon</b>.")

st.subheader("Comment utiliser l'interface")
st.markdown("""
- Le menu à gauche donne une page par étape, plus une **fiche par titre**.
- Par défaut, chaque page affiche **les résultats du projet** : ce sont les mêmes chiffres que dans les notebooks et la présentation.
- Les réglages (k, taux de contamination, taux sans risque, titres liquides seulement) permettent d'**explorer**. Quand un réglage s'écarte du projet, la page le signale.
""")
st.caption("Les calculs reprennent exactement ceux des notebooks S3, S4 et S4b ; le script app/verifier_coherence.py le contrôle (21 contrôles).")
