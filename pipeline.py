#!/usr/bin/env python3
"""Collecte et calcul de l'indicateur principal d'usage en production.
Python 3.10+, bibliothèque standard uniquement.
"""
import gzip, argparse, datetime as dt, json, math, os, re, sys, tempfile, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent
IDS = {
    'production': 'fr-en-assistant_ia_deploiement_menjs',
    'beta': 'assistant-ia-dinum-deploiement-au-ministere-de-leducation-nationale-en-academie',
}
CATS = ['administration','enseignants','chefs_d_etablissement','inspecteurs']

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def atomic(p, content):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',dir=p.parent,delete=False,encoding='utf-8') as f:
        f.write(content); tmp=f.name
    os.replace(tmp,p)
def save(p,obj): atomic(p,json.dumps(obj,ensure_ascii=False,indent=2))
def domain(s): return re.sub('[^a-z0-9]','_',s.lower().lstrip('@'))
def number(x): return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and x>=0
def day(r): return dt.datetime.fromisoformat(r['timestamp']).date().isoformat()

def intensity(rows,key,date):
    start=(dt.date.fromisoformat(date)-dt.timedelta(days=7)).isoformat()
    by={day(r):r for r in rows}
    if date not in by or start not in by: return None,'Observation exacte à J ou J−7 absente'
    window=sorted((r for r in rows if start<=day(r)<=date),key=day)
    for field in [key+'_users',key+'_messages']:
        if any(not number(r.get(field)) for r in window): return None,'Champ manquant ou invalide'
        if any(b[field]<a[field] for a,b in zip(window,window[1:])): return None,'Diminution de compteur sur la fenêtre'
    a,b=by[start],by[date]; denom=(a[key+'_users']+b[key+'_users'])/2
    if not denom: return None,'Dénominateur nul'
    return (b[key+'_messages']-a[key+'_messages'])/denom,None

def validate(bundle):
    for n in IDS:
        obj=bundle[n+'_records']; meta=bundle[n+'_metadata']
        if len(obj['results'])!=obj['total_count']: raise ValueError(n+': extraction incomplète')
        if not obj['results']: raise ValueError(n+': extraction vide')
        if meta.get('dataset_id')!=IDS[n]: raise ValueError('Identité source incorrecte pour '+n)
    prod=bundle['production_records']['results']; beta=bundle['beta_records']['results']
    dates=[day(r) for r in prod]
    if len(dates)!=len(set(dates)): raise ValueError('Doublon de date production')
    names=[r['email_academie'] for r in beta]
    if len(names)!=len(set(names)): raise ValueError('Doublon de domaine bêta')
    fields={f['name'] for f in bundle['production_metadata']['fields']}
    for r in beta:
        if not r.get('libelle_aca') or not r.get('email_academie'): raise ValueError('Identité territoriale bêta manquante')
        for k in CATS+['total']:
            if not number(r.get(k)) or int(r[k])!=r[k]: raise ValueError('Volume bêta manquant/invalide')
        if sum(r[k] for k in CATS)!=r['total']: raise ValueError('Total bêta incohérent')
        for k in ['users','messages']:
            if domain(r['email_academie'])+'_'+k not in fields: raise ValueError('Correspondance production absente')
        g=r.get('geopoint') or {}
        if not isinstance(g.get('lat'),(int,float)) or not isinstance(g.get('lon'),(int,float)): raise ValueError('Coordonnées invalides')
    return sorted(prod,key=day), sorted(beta,key=lambda r:r['libelle_aca'])

def weekly_end(latest, anchor):
    latest=dt.date.fromisoformat(latest); anchor=dt.date.fromisoformat(anchor)
    return (latest-dt.timedelta(days=(latest-anchor).days % 7)).isoformat()

def median_week(rows, keys, end, fraction=.5):
    start=(dt.date.fromisoformat(end)-dt.timedelta(days=7)).isoformat()
    vals=[]
    for k in keys:
        v,_=intensity(rows,k,end)
        if v is None:
            return {'start':start,'end':end,'median':None,'threshold':None,'reason':'Une ou plusieurs académies sont non calculables'}
        vals.append(v)
    vals=sorted(vals); n=len(vals)
    median=(vals[n//2] if n%2 else (vals[n//2-1]+vals[n//2])/2)
    return {'start':start,'end':end,'median':median,'threshold':median*fraction,'reason':None,'territories':n}

def detect_signal(current, previous, current_threshold, previous_threshold):
    if any(v is None for v in [current,previous,current_threshold,previous_threshold]): return 'Non calculable'
    if current<current_threshold and previous<previous_threshold: return 'Signal sur deux semaines'
    if current<current_threshold: return 'Sous le seuil cette semaine'
    return 'Pas de signal persistant'

def build(bundle,rule=None):
    prod,beta=validate(bundle)
    date=day(prod[-1])
    rule=rule or read(ROOT/'config/indicator.json')
    keys=[domain(d) for d in rule['scope_domains']]
    if rule.get('fraction')!=.5 or rule.get('consecutive_weeks')!=2: raise ValueError('Règle d’alerte inattendue')
    production_fields={f['name'] for f in bundle['production_metadata']['fields']}
    if any(k+'_users' not in production_fields or k+'_messages' not in production_fields for k in keys): raise ValueError('Périmètre territorial absent de la production')
    analysis_date=weekly_end(date,rule['anchor_date'])
    previous_date=(dt.date.fromisoformat(analysis_date)-dt.timedelta(days=7)).isoformat()
    current=median_week(prod,keys,analysis_date,rule['fraction']); previous=median_week(prod,keys,previous_date,rule['fraction'])
    by={day(x):x for x in prod}; rows=[]
    for r in beta:
        k=domain(r['email_academie']); i,reason=intensity(prod,k,analysis_date); prev,prev_reason=intensity(prod,k,previous_date)
        signal=detect_signal(i,prev,current['threshold'],previous['threshold'])
        history=[{'date':day(x),'users':x.get(k+'_users'),'messages':x.get(k+'_messages'),'intensity':intensity(prod,k,day(x))[0]} for x in prod]
        rows.append({**r,
          'beta_registrations':r['total'],
          'intensity':i,'intensity_reason':reason,'previous_intensity':prev,'previous_intensity_reason':prev_reason,
          'signal':signal,'signal_context':'Signal statistique à contextualiser ; il ne mesure ni la qualité ni l’utilité des usages.',
          'production_users':by.get(analysis_date,{}).get(k+'_users'),
          'production_messages':by.get(analysis_date,{}).get(k+'_messages'),
          'history':history})
    aggregate=[]
    for item in prod:
        vals=[]
        for k in keys:
            v,_=intensity(prod,k,day(item))
            if v is not None: vals.append(v)
        
        if vals:
            vals=sorted(vals); n=len(vals); med=(vals[n//2] if n%2 else (vals[n//2-1]+vals[n//2])/2)
        else: med=None
        aggregate.append({'date':day(item),'users':sum(item.get(k+'_users',0) for k in keys),'messages':sum(item.get(k+'_messages',0) for k in keys),'intensity':med})
    dates={day(r) for r in prod}; start=dt.date.fromisoformat(min(dates)); end=dt.date.fromisoformat(max(dates))
    missing=[str(start+dt.timedelta(days=i)) for i in range((end-start).days+1) if str(start+dt.timedelta(days=i)) not in dates]
    counter_fields=[f['name'] for f in bundle['production_metadata']['fields'] if f['type']=='int']
    decreases=[{'field':f,'date':day(z)} for a,z in zip(prod,prod[1:]) for f in counter_fields if number(a.get(f)) and number(z.get(f)) and z[f]<a[f]]
    beta_total=sum(r['total'] for r in beta)
    prod_users=sum(by.get(analysis_date,{}).get(k+'_users',0) for k in keys)
    prod_messages=sum(by.get(analysis_date,{}).get(k+'_messages',0) for k in keys)
    return {
      'generated_at':now(),'collected_at':bundle['collection']['collected_at'],
      'production_date':date,'production_start':min(dates),'analysis_date':analysis_date,
      'weekly':{'current':current,'previous':previous,'rule':rule},
      'source_dates':{n:bundle[n+'_metadata']['metas']['default']['data_processed'] for n in IDS},
      'rows':rows,'aggregate_history':aggregate,
      'quality':{'production_observations':len(prod),'beta_territories':len(beta),'missing_dates':missing,'negative_changes':decreases,
                 'beta_total_registrations':beta_total,'production_users_32':prod_users,'production_messages_32':prod_messages,
                 'signals_persistent':sum(r['signal']=='Signal sur deux semaines' for r in rows)},
      'interpretation':{
        'primary_indicator':'Intensité d’usage hebdomadaire en production',
        'beta_role':'Contexte historique : inscriptions finales à la bêta, figées depuis juin 2026',
        'warning':'Les inscriptions bêta et les comptes de production ne sont ni additionnés ni rapportés comme un taux de conversion.'
      }
    }

def fetch():
    bundle={}
    for name,ds in IDS.items():
        base='https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/'+ds
        def get(url):
            with urllib.request.urlopen(url,timeout=90) as response:
                raw=response.read(); return json.loads(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw)
        bundle[name+'_metadata']=get(base)
        allrows=[]; offset=0
        while True:
            page=get(base+'/records?limit=100&offset='+str(offset)); allrows.extend(page['results']); offset+=len(page['results'])
            if offset>=page['total_count']: break
            if not page['results']: raise ValueError('Pagination interrompue')
        bundle[name+'_records']={'total_count':page['total_count'],'results':allrows}
    bundle['collection']={'collected_at':now(),'method':'API Explore v2.1, pagination 100'}
    return bundle

def render(data,status,root=ROOT):
    payload=json.dumps({'data':data,'status':status},ensure_ascii=False).replace('</','<\\/')
    geography=read(root/'assets/academies.json') if (root/'assets/academies.json').exists() else []
    template=(root/'template.html').read_text(encoding='utf-8').replace('/*PAYLOAD*/',payload).replace('/*GEOGRAPHY*/',json.dumps(geography,ensure_ascii=False))
    atomic(root/'dashboard.html',template)

def normalized_reference_bundle(source_dir):
    """Accepte aussi l'archive antérieure à l'erratum où les fichiers beta/production étaient nommés à l'envers."""
    bundle={p.stem:read(p) for p in source_dir.glob('*.json')}
    if bundle.get('beta_metadata',{}).get('dataset_id')==IDS['production']:
        for suffix in ['metadata','records']:
            bundle['beta_'+suffix],bundle['production_'+suffix]=bundle['production_'+suffix],bundle['beta_'+suffix]
    return bundle

def run(root=ROOT,offline=False,reference_mode=False):
    dest=root/'data/dashboard.json'
    try:
        source_dir=root/('data/reference_2026-10-01' if reference_mode else 'data/raw')
        bundle=normalized_reference_bundle(source_dir) if (offline or reference_mode) else fetch()
        data=build(bundle,read(root/'config/indicator.json'))
        status={'ok':True,'attempt_at':now(),'mode':'Référence au 01/10/2026' if reference_mode else ('Extraction hors ligne' if offline else 'Collecte API exécutée'),'scheduler':'Non déployé dans ce livrable'}
        render(data,status,root); save(dest,data); save(root/'data/status.json',status)
        print(json.dumps({'ok':True,'date':data['production_date'],'threshold':data['weekly']['current']['threshold'],'signals':[r['libelle_aca'] for r in data['rows'] if r['signal']=='Signal sur deux semaines']},ensure_ascii=False))
        return 0
    except Exception as e:
        status={'ok':False,'attempt_at':now(),'error':str(e),'mode':'Dernier résultat valide conservé','scheduler':'Vérifier le journal'}
        save(root/'data/status.json',status)
        if dest.exists(): render(read(dest),status,root)
        print(str(e),file=sys.stderr); return 1

if __name__=='__main__':
    parser=argparse.ArgumentParser(); group=parser.add_mutually_exclusive_group(); group.add_argument('--offline',action='store_true'); group.add_argument('--reference',action='store_true'); args=parser.parse_args(); sys.exit(run(offline=args.offline,reference_mode=args.reference))
