import pandas as pd, numpy as np
R='/home/claude/full/'
def esc(s): 
    s=str(s)
    for a,b in [('\\','\\textbackslash{}'),('&','\\&'),('%','\\%'),('_','\\_'),('#','\\#'),('$','\\$')]: s=s.replace(a,b)
    return s
def n(x,d=2): return f"{x:.{d}f}".replace('.','{,}').replace('-','$-$')
def p(x,d=1): return f"{x*100:.{d}f}".replace('.','{,}').replace('-','$-$')+"~\\%"
f=pd.read_csv(R+'data/s3/features_titres.csv').set_index('ticker')
q=pd.read_csv(R+'data/processed/qualite_par_titre.csv').dropna(subset=['ticker']).set_index('ticker')
r4=pd.read_csv(R+'data/processed/s4/resultats_par_titre.csv').set_index('ticker')
r5=pd.read_csv(R+'data/processed/s4_5f/resultats_par_titre.csv').set_index('ticker')
T=sorted(f.index)
# --- titres
L=[r"\begin{longtable}{llrrcccccc}",r"\caption{Les 75 titres : liquidité, groupes k-means et signalements Isolation Forest}\label{tab:annexe-titres}\\",
 r"\toprule Ticker & Nom & Séances & Rdts nuls & Liq. & RV & 7F & ACP & 5F & IF/12 \\ \midrule \endfirsthead",
 r"\toprule Ticker & Nom & Séances & Rdts nuls & Liq. & RV & 7F & ACP & 5F & IF/12 \\ \midrule \endhead \bottomrule \endfoot"]
for t in T:
    L.append(f"{esc(t)} & {esc(q.loc[t,'nom'])[:28]} & {p(q.loc[t,'part_seances_echangees'],0)} & {p(q.loc[t,'part_rendements_nuls'],0)} & {'oui' if q.loc[t,'part_seances_echangees']>=0.6 else 'non'} & {r4.loc[t,'cluster_RV']} & {r4.loc[t,'cluster_7F']} & {r4.loc[t,'cluster_ACP']} & {r5.loc[t,'cluster_5F']} & {r4.loc[t,'nb_signalements_sur_12']} \\\\")
L.append(r"\end{longtable}")
open('annexes/tab_titres.tex','w').write('\n'.join(L))
# --- features
L=[r"\begin{longtable}{lrrrrrrr}",r"\caption{Les 7 features des 75 titres (rendement et volatilité annualisés ; VaR et CVaR journalières à 95~\%)}\label{tab:annexe-features}\\",
 r"\toprule Ticker & Rendement & Volatilité & Skewness & Kurtosis & VaR & CVaR & Bêta \\ \midrule \endfirsthead",
 r"\toprule Ticker & Rendement & Volatilité & Skewness & Kurtosis & VaR & CVaR & Bêta \\ \midrule \endhead \bottomrule \endfoot"]
for t in T:
    x=f.loc[t]; L.append(f"{esc(t)} & {p(x.rendement_annualise)} & {p(x.volatilite_annualisee)} & {n(x['skewness'])} & {n(x['kurtosis'])} & {p(x.var_95,2)} & {p(x.cvar_95,2)} & {n(x.beta)} \\\\")
L.append(r"\end{longtable}")
open('annexes/tab_features.tex','w').write('\n'.join(L))
# --- criteres k
def crit(path,titre,label):
    c=pd.read_csv(path)
    L=[r"\begin{table}[H]\centering\small",f"\\caption{{{titre}}}\\label{{{label}}}",r"\begin{tabular}{llrrrrl}\toprule",
       r"Espace & $k$ & Inertie & Silhouette & CH & DB & Tailles \\ \midrule"]
    for e,g in c.groupby('espace',sort=False):
        for _,x in g.iterrows():
            L.append(f"{e} & {x.k} & {n(x.inertie,1)} & {n(x.silhouette,3)} & {n(x.calinski_harabasz,1)} & {n(x.davies_bouldin,3)} & {x.tailles} \\\\")
        L.append(r"\midrule")
    L[-1]=r"\bottomrule\end{tabular}\end{table}"
    return '\n'.join(L)
s=crit(R+'data/processed/s4/choix_k_criteres.csv',"Critères de choix de $k$, 75 titres (S4)","tab:annexe-k75")
s+="\n"+crit(R+'data/processed/s4/choix_k_criteres_liquides.csv',"Critères de choix de $k$, 57 titres liquides (S4)","tab:annexe-k57")
c5=pd.read_csv(R+'data/processed/s4_5f/choix_k_criteres.csv'); c5.insert(0,'espace','5F'); c5.to_csv('/tmp/c5.csv',index=False)
c57=pd.read_csv(R+'data/processed/s4_5f/choix_k_criteres_liquides.csv'); c57.insert(0,'espace','5F (57)'); pd.concat([c5,c57]).to_csv('/tmp/c5b.csv',index=False)
s+="\n"+crit('/tmp/c5b.csv',"Critères de choix de $k$, 5 features (S4b) : 75 titres et 57 liquides","tab:annexe-k5f")
open('annexes/tab_criteres_k.tex','w').write(s)
# --- stabilite
def stab(path,titre,label,espace=True):
    c=pd.read_csv(path)
    L=[r"\begin{table}[H]\centering\small",f"\\caption{{{titre}}}\\label{{{label}}}",r"\begin{tabular}{"+("ll" if 'espace' in c else "l")+r"rp{9cm}}\toprule",
       ("Espace & " if 'espace' in c else "")+r"Taux & Signalés & Titres \\ \midrule"]
    for _,x in c.iterrows():
        L.append((f"{x.espace} & " if 'espace' in c else "")+f"{esc(x.taux)} & {x.nb_signales} & {esc(x.titres_signales)} \\\\")
    L.append(r"\bottomrule\end{tabular}\end{table}"); return '\n'.join(L)
s=stab(R+'data/processed/s4/stabilite_isolation_forest.csv',"Titres signalés par Isolation Forest, 75 titres (S4)","tab:annexe-if75")
s+="\n"+stab(R+'data/processed/s4/stabilite_isolation_forest_liquides.csv',"Titres signalés par Isolation Forest, 57 titres liquides (S4)","tab:annexe-if57")
s+="\n"+stab(R+'data/processed/s4_5f/stabilite_isolation_forest.csv',"Titres signalés par Isolation Forest, 5 features, 75 titres (S4b)","tab:annexe-if5f")
s+="\n"+stab(R+'data/processed/s4_5f/stabilite_isolation_forest_liquides.csv',"Titres signalés par Isolation Forest, 5 features, 57 titres liquides (S4b)","tab:annexe-if5f57")
open('annexes/tab_stabilite.tex','w').write(s)
# --- poids
ms=pd.read_csv(R+'data/s3/markowitz_sharpe_maximal.csv').set_index('ticker').poids
gm=pd.read_csv(R+'data/s3/markowitz_variance_minimale.csv').set_index('ticker')
ms=ms[ms>1e-3].sort_values(ascending=False); g=gm.sort_values('poids_sans_vente_a_decouvert',ascending=False).head(15)
L=[r"\begin{table}[H]\centering\small\caption{Poids des portefeuilles de Markowitz (75 titres, sans vente à découvert)}\label{tab:annexe-poids}",
   r"\begin{tabular}{lr@{\hspace{1.2cm}}lr@{\hspace{1.2cm}}lrr}\toprule",
   r"\multicolumn{4}{c}{Sharpe maximal (33 titres $>$ 0,1~\%)} & \multicolumn{3}{c}{Variance minimale (15 premiers)}\\ \cmidrule(r){1-4}\cmidrule(l){5-7}",
   r"Titre & Poids & Titre & Poids & Titre & $w \geq 0$ & forme fermée \\ \midrule"]
a=list(ms.items()); h=(len(a)+1)//2; gl=list(g.iterrows())
for k in range(h):
    t1=f"{esc(a[k][0])} & {p(a[k][1])}"; t2=f"{esc(a[k+h][0])} & {p(a[k+h][1])}" if k+h<len(a) else " & "
    t3=f"{esc(gl[k][0])} & {p(gl[k][1].poids_sans_vente_a_decouvert)} & {p(gl[k][1].poids_forme_fermee)}" if k<len(gl) else " & & "
    L.append(f"{t1} & {t2} & {t3} \\\\")
L.append(r"\bottomrule\end{tabular}\end{table}")
open('annexes/tab_poids.tex','w').write('\n'.join(L))
# --- OST
o=pd.read_csv('/mnt/user-data/uploads/Projet Math Assurance/data/processed/operations_sur_titres.csv',parse_dates=['date'])
ct=pd.crosstab(o.type,o.date.dt.year,margins=True,margins_name='Total')
L=[r"\begin{table}[H]\centering\small\caption{Opérations sur titres détectées par le cours de référence officiel, par type et par année}\label{tab:annexe-ost}",
   r"\begin{tabular}{l"+"r"*len(ct.columns)+r"}\toprule","Type & "+" & ".join(map(str,ct.columns))+r" \\ \midrule"]
for i_,x in ct.iterrows():
    if i_=='Total': L.append(r"\midrule")
    L.append(esc(i_)+" & "+" & ".join(map(str,x.values))+r" \\")
L.append(r"\bottomrule\end{tabular}\end{table}")
b=o[o.ticker=='BIAT']
L+=[r"\begin{table}[H]\centering\small\caption{Exemple : les 5 opérations sur titres de BIAT}\label{tab:annexe-biat}",r"\begin{tabular}{llrrrp{5cm}}\toprule",
    r"Date & Type & Clôture veille & Référence & Facteur & Détail \\ \midrule"]
for _,x in b.iterrows():
    L.append(f"{x.date:%d/%m/%Y} & {esc(x.type)} & {n(x.cloture_veille)} & {n(x.reference)} & {n(x.facteur,4)} & {esc(x.detail)} \\\\")
L.append(r"\bottomrule\end{tabular}\end{table}")
open('annexes/tab_ost.tex','w').write('\n'.join(L))
print('ok')
