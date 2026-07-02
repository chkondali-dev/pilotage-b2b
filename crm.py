import pandas as pd
from pathlib import Path
import unicodedata
import warnings
warnings.filterwarnings('ignore')

# --- CONFIG ---
SRC = Path(r'C:\Users\hachk\OneDrive - Société Magasin Général (SMG)\Documents\hamadi\grands compte\hamadi\dashbord convention\table vente\2025\TDC2.xlsx')
DST = Path(r'C:\Users\hachk\pilotage_b2b\TDC CONVENTION 1.xlsm')
S_SRC = 'convention en cours'
S_DATA = 'DATA_CRM'
S_CRM = 'CRM'

def _norm(name):
    nfkd = unicodedata.normalize('NFKD', str(name))
    ascii_ = nfkd.encode('ascii', 'ignore').decode('ascii')
    return ' '.join(ascii_.strip().lower().split())

def _rename(cols, mapping):
    idx = {_norm(c): c for c in cols}
    ren = {}
    for nk, tv in mapping.items():
        if nk in idx:
            ren[idx[nk]] = tv
    return ren

CM = {
    'conventions en cours': 'Nom entreprise',
    'prive ou etathique': 'Secteur',
    "nbr d'effectifs": 'Effectifs',
    'coordonnees': 'Contact',
    'contacts': 'Telephone',
    'email': 'Email',
    'avancement2': 'Statut pipeline',
    'ranking': 'Priorite relance',
    'commentaire': 'Commentaire',
    'commentaire fathi': 'Commentaire fathi',
    "taux d'interet": 'Taux interet',
    'ristourne': 'Ristourne',
    'avantages supplementaires': 'Avantages supp',
    'mode de paiement': 'Mode paiement',
    'niveau salaire': 'Niveau salaire',
    'titualire': 'Titulaire',
    'etat': 'Etat',
    'colonne1': 'ID',
    'colonne2': 'Flag1',
    'colonne3': 'Flag2',
    'colonne4': 'Flag3',
    'colonne5': 'Flag4',
    'colonne6': 'Flag5',
    'prospection': 'Type prospection',
}
BM = {
    'prise de contact': 'Prise contact',
    'validation client': 'Validation client',
    'juridique': 'Juridique',
    'finance': 'Finance',
    'signature': 'Signature',
}
DM = {
    'date prise de contact': 'Date prise contact',
    'date validation client': 'Date validation client',
    'date juridique': 'Date juridique',
    'date fianance': 'Date finance',
    'date signature': 'Date signature',
}

def load_crm_data(source=None):
    if source is None:
        _src = SRC
        if not _src.exists():
            raise FileNotFoundError(f'Source introuvable: {SRC}')
        df = pd.read_excel(_src, sheet_name=S_SRC, header=12)
    else:
        df = pd.read_excel(source, sheet_name=S_SRC, header=12)
    df = df.dropna(axis=1, how='all')
    df = df.dropna(subset=[df.columns[1]]).reset_index(drop=True)
    df = df.rename(columns=_rename(df.columns, CM))
    bm = _rename([c for c in df.columns if _norm(c) in BM], BM)
    df = df.rename(columns=bm)
    for c in bm.values():
        if c in df.columns:
            def _tb(x):
                if x in [True, 1, 'Vrai', 'true', 'True']:
                    return True
                if x in [False, 0, 'Faux', 'false', 'False', None]:
                    return False
                if isinstance(x, str) and x.startswith('Vrai'):
                    return True
                return None
            df[c] = df[c].apply(_tb)
    dm = _rename([c for c in df.columns if _norm(c) in DM], DM)
    df = df.rename(columns=dm)
    for c in dm.values():
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce', dayfirst=True)
    dcols = [c for c in dm.values() if c in df.columns]
    if dcols:
        df['Date derniere activite'] = df[dcols].max(axis=1)
    df['Prochaine relance'] = pd.NaT
    if 'Taux interet' in df.columns and 'Effectifs' in df.columns:
        df['Taux interet'] = pd.to_numeric(df['Taux interet'], errors='coerce').fillna(0)
        df['Effectifs'] = pd.to_numeric(df['Effectifs'], errors='coerce').fillna(0)
        df['CA potentiel'] = (df['Taux interet'] * df['Effectifs']).round(2)
    else:
        df['CA potentiel'] = 0.0
    df['CA realise'] = 0.0
    # Accent-insensitive statut pipeline
    if 'Statut pipeline' in df.columns:
        raw = df['Statut pipeline'].fillna('').astype(str).str.strip()
        norm = raw.apply(lambda x: unicodedata.normalize('NFKD', x).encode('ascii','ignore').decode('ascii').lower().strip())
        mp = {'cloture': 'Cloture', 'en cours': 'En cours', 'non demarre': 'Non demarre'}
        df['Statut pipeline'] = norm.map(mp).fillna('Non demarre')
    # Priorite from stars
    if 'Priorite relance' in df.columns:
        df['Priorite relance'] = df['Priorite relance'].fillna('').astype(str).str.strip()
        sm = {}
        sm[chr(127775)*4] = 'Haute'
        sm[chr(127775)*3] = 'Haute'
        sm[chr(127775)*2] = 'Moyenne'
        sm[chr(127775)] = 'Basse'
        sm[''] = 'Non defini'; sm['nan'] = 'Non defini'; sm['None'] = 'Non defini'
        df['Priorite relance'] = df['Priorite relance'].replace(sm)
        df['Priorite relance'] = df['Priorite relance'].apply(lambda x: 'Haute' if isinstance(x, str) and chr(127775) in x else x)
    # Secteur
    if 'Secteur' in df.columns:
        df['Secteur'] = df['Secteur'].fillna('').astype(str).str.strip()
        df['Secteur'] = df['Secteur'].apply(lambda x: unicodedata.normalize('NFKD', x).encode('ascii','ignore').decode('ascii').strip().lower())
        sm2 = dict(prive='Prive', etatique='Etatique')
        sm2['prive offshore'] = 'Prive Off Shore'
        df['Secteur'] = df['Secteur'].map(sm2).fillna('Non defini')
    df['Magasin'] = 'General'
    df['Responsable commercial'] = df.get('Contact', '').fillna('')
    for c in ['CA potentiel', 'CA realise']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df

def export_to_excel(df):
    import xlwings as xw
    app = xw.App(visible=False)
    try:
        wb = app.books.open(str(DST))
        for s in wb.sheets:
            if s.name == S_DATA:
                s.delete()
        ws = wb.sheets.add(S_DATA)
        ws.range('A1').value = df.columns.tolist()
        ws.range('A2').value = df.values.tolist()
        lr = len(df) + 1
        lc = chr(64 + len(df.columns))
        rng = ws.range(f'A1:{lc}{lr}')
        tbl = ws.api.ListObjects.Add(SourceType=1, SourceData=rng.api, LinkSource=False, XlListObjectHasHeaders=True)
        tbl.Name = S_DATA
        ws.api.Columns.AutoFit()
        wb.save()
        print(f'[OK] {S_DATA}: {len(df)} lignes')
    finally:
        app.quit()

def _pt(ws, cache, name, rows, values, pos):
    pt = ws.api.PivotTables().Add(PivotCache=cache, TableDestination=ws.range(pos).api, TableName=name)
    for i, rf in enumerate(rows):
        pf = pt.PivotFields(rf); pf.Orientation = 1; pf.Position = i + 1
    for vn, vf, vfn in values:
        pf = pt.PivotFields(vf); pt.AddDataField(pf, vn, vfn)

def create_pivot_tables():
    import xlwings as xw
    app = xw.App(visible=False)
    try:
        wb = app.books.open(str(DST))
        if S_DATA not in [s.name for s in wb.sheets]:
            print('[ERR] DATA_CRM absent'); return
        dr = wb.sheets[S_DATA].range('A1').expand('table')
        cache = wb.api.PivotCaches().Create(SourceType=1, SourceData=dr.api)
        if S_CRM in [s.name for s in wb.sheets]:
            ws = wb.sheets[S_CRM]
            for pt in ws.api.PivotTables(): pt.TableRange2.Clear()
            ws.clear()
        else:
            ws = wb.sheets.add(S_CRM)
        _pt(ws, cache, 'PipelinePivot', ['Statut pipeline'],
            [('Nb prospects', 'Statut pipeline', -4112),
             ('Somme CA potentiel', 'CA potentiel', -4157),
             ('Somme CA realise', 'CA realise', -4157)], 'B2')
        _pt(ws, cache, 'RelancePivot', ['Priorite relance'],
            [('Nb prospects', 'Priorite relance', -4112)], 'F2')
        _pt(ws, cache, 'PerfPivot', ['Responsable commercial'],
            [('CA realise', 'CA realise', -4157),
             ('CA potentiel', 'CA potentiel', -4157)], 'B10')
        _pt(ws, cache, 'MagasinPivot', ['Magasin'],
            [('CA realise', 'CA realise', -4157),
             ('Nb conventions', 'Nom entreprise', -4112)], 'F10')
        ws.api.Columns.AutoFit()
        wb.save()
        print('[OK] 4 TCD crees dans CRM')
    finally:
        app.quit()

def update_crm_dashboard():
    print('=== Mise a jour Dashboard CRM ===')
    print(f'Source: {SRC.name}')
    print(f'Destination: {DST.name}')
    df = load_crm_data()
    print(f'Charge: {len(df)} prospects')
    export_to_excel(df)
    create_pivot_tables()
    print('[OK] Dashboard CRM pret')

if __name__ == '__main__':
    update_crm_dashboard()
