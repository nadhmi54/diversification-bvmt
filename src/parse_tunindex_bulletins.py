import re, pymupdf, pandas as pd
from pathlib import Path
import parse_bulletins as pb
NUM=r"(\d{1,3}(?: \d{3})*,\d{2})"
def clean(s): return re.sub(r'\s+',' ',str(s).replace(' ',' ').replace('\xa0',' '))
def val(s): return float(s.replace(' ','').replace(',','.'))
def lire(p):
    doc=pymupdf.open(p); out={}
    t=clean(doc[0].get_text())
    for k,lab in (('tunindex','TUNINDEX'),('tunindex20','TUNINDEX20')):
        m=re.search(lab+r" (?:Variation du jour Variation sur l.ann.e )?"+NUM,t)
        if m: out[k]=val(m[1])
    if len(out)<2:
        for tab in doc[0].find_tables().tables:
            for row in tab.extract():
                for c in row:
                    c=clean(c)
                    for k,lab in (('tunindex','TUNINDEX'),('tunindex20','TUNINDEX20')):
                        m=re.match(lab+r" "+NUM,c)
                        if m and k not in out: out[k]=val(m[1])
    out['seance']=pb.date_du_texte(doc); out['fichier']=p.name
    return out
rows=[lire(p) for p in sorted(Path('data/raw/bulletins/pdf').glob('*.pdf'))]
df=pd.DataFrame(rows).sort_values('seance'); df.to_csv('data/interim/tunindex_2026.csv',index=False)
print(df.shape, df.tunindex.isna().sum(), df.tunindex20.isna().sum()); print(df.head(3)); print(df.iloc[65:75])
