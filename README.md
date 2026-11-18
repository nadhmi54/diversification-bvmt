# Diversification par apprentissage non supervisé sur la BVMT

Projet Math en assurance et finance — 5INFINI, ESPRIT, A.U. 2026-2027.

Le projet reprend, critique et prolonge l'article de Rebai, Boukhris, Ncib et Ben Lasmar (2021),
*Unsupervised Learning Diversification Applied on the Tunisian Stock Market Before and During the Covid-19 Crisis*.
Données : actions cotées à la Bourse de Tunis du **02/01/2023 au 03/11/2026** (extraction du 04/11/2026),
uniquement à partir de **sources officielles** de la Bourse (archives annuelles 2023-2025, bulletins officiels quotidiens 2026).

## Avancement

| Séance | Contenu | Où |
|---|---|---|
| S1 | Analyse critique de l'article de référence | rapport (hors dépôt) |
| S2 | Collecte, nettoyage, opérations sur titres, filtres, note qualité | `src/`, `data/processed/`, `reports/note_qualite_donnees.md` |
| S3 | 7 features par titre, covariance, Markowitz (variance minimale, Sharpe maximal, frontière) | `notebooks/S3_features_markowitz.ipynb`, `data/s3/`, `reports/S3_Features_Markowitz_BVMT.pdf` |
| S4 | Standardisation, ACP, k-means (3 espaces), Isolation Forest, interprétation, comparaison 75 / 57 titres | `notebooks/S4_segmentation_anomalies.ipynb`, `data/processed/s4/` |

## Structure

```
src/                     scripts de la S2 (collecte, extraction des bulletins PDF, construction du jeu de données)
notebooks/               S3 et S4, exécutables de bout en bout (chemins relatifs, graine fixe)
data/raw/                données brutes — NON versionnées (voir ci-dessous), sauf manifeste_bulletins.csv
data/interim/            extractions intermédiaires des bulletins 2026
data/processed/          jeu de données de la S2 ; sorties de la S4 dans data/processed/s4/
data/s3/                 sorties de la S3
reports/                 note qualité (S2) et rapport PDF de la S3
```

## Reproduire

```bash
pip install -r requirements.txt

# S2 — données (les données brutes ne sont pas dans le dépôt : on les retélécharge)
python src/collecte.py                                    # -> data/raw/  (sources officielles BVMT)
python src/parse_bulletins.py data/raw/bulletins/pdf      # -> data/interim/bulletins_2026.csv  (~3 min)
python src/parse_tunindex_bulletins.py                    # -> data/interim/tunindex_2026.csv
python src/build_dataset.py                               # -> data/processed/*

# S3 et S4 — à lancer depuis le dossier notebooks/
jupyter nbconvert --to notebook --execute --inplace notebooks/S3_features_markowitz.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/S4_segmentation_anomalies.ipynb
```

`src/unpack_bulletins.py` ne sert que pour les paquets `.bin` produits par la collecte initiale faite depuis un navigateur.
La liste exacte des 209 bulletins utilisés (URL, taille, date d'extraction) est dans `data/raw/bulletins/manifeste_bulletins.csv`.

## Choix principaux

- **Univers** : 75 actions cotées au 03/11/2026, dont 57 liquides (au moins 60 % de séances avec une transaction).
  Les résultats sont donnés sur les 75 titres et sur les 57 titres liquides.
- **Opérations sur titres** : neutralisées par le cours de référence officiel (dividendes, attributions gratuites, divisions).
- **Rendements** : logarithmiques journaliers ; features et covariance annualisées (× 252).
- **Taux sans risque** : TMM d'octobre 2026 (7 %), converti en taux continu ln(1,07) = 6,77 %.
- **Limites connues** : volumes 2026 non publiés dans les bulletins ; biais du survivant (10 sociétés radiées depuis 2023
  hors univers) ; résultats en échantillon, le test hors échantillon relève de la Phase 3.

## Usage de l'IA générative

Une partie du code et de la rédaction a été produite avec l'aide d'un assistant IA. Cet usage est déclaré
en annexe du rapport, conformément au cahier des charges.
