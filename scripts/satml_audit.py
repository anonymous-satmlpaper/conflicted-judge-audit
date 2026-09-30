"""Offline integrity and statistical audit. Never modifies legacy inputs."""
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import binomtest, fisher_exact, rankdata, wilcoxon
import krippendorff

ROOT = Path(__file__).resolve().parents[1]
DIMS = ['support', 'provenance', 'obs_inf', 'attribution', 'reproducibility']

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def clean(x):
    if isinstance(x, dict): return {k: clean(v) for k,v in x.items()}
    if isinstance(x, (list, tuple)): return [clean(v) for v in x]
    if isinstance(x, np.generic): x = x.item()
    if isinstance(x, float) and not np.isfinite(x): return None
    return x

def main():
    cases = {p.stem: read(p) for p in sorted((ROOT/'cases').glob('AND-*.json'))}
    records = [read(p) for p in sorted((ROOT/'outputs/harness').glob('*.json'))]
    scores = read(ROOT/'scoring/all_scores.json')
    groups = defaultdict(list)
    for s in scores:
        assert s['case_id'] in cases
        assert all(type(s[d]) is int and s[d] in [0,1,2] for d in DIMS)
        groups[s['case_id'], s['model_requested']].append(s)
    models = sorted({r['model_requested'] for r in records})
    keys = [(r['case_id'],r['model_requested']) for r in records]
    assert len(keys) == len(set(keys))
    assert set(keys) == set(groups)
    assert set(keys) == set(itertools.product(cases, models))
    prompt_mismatches = []
    for r in records:
        c = cases[r['case_id']]
        expected = c['task_prompt'].replace('{ARTIFACTS_JSON}', json.dumps(c['artifacts'], indent=2))
        if expected != r['prompt']: prompt_mismatches.append([r['case_id'],r['model_requested']])
    means = {k: {d: np.mean([s[d] for s in g]) for d in DIMS} for k,g in groups.items()}
    rows = {}
    for m in models:
        ss = [s for s in scores if s['model_requested']==m]
        rows[m] = {
            'responses': sum(r['model_requested']==m for r in records),
            'claims': len(ss),
            'served_models': dict(Counter(r['model_served_by'] for r in records if r['model_requested']==m)),
            'stop_reasons': dict(Counter(r['stop_reason'] for r in records if r['model_requested']==m)),
            'claim_weighted': {d: np.mean([s[d] for s in ss]) for d in DIMS},
            'case_weighted': {d: np.mean([means[c,m][d] for c in cases]) for d in DIMS},
        }
    comparisons=[]
    for a,b in itertools.combinations(models,2):
        x=np.array([np.mean(list(means[c,a].values())) for c in cases])
        y=np.array([np.mean(list(means[c,b].values())) for c in cases])
        delta=np.round(x-y,12)
        nz=delta[delta!=0]
        ranks=rankdata(abs(nz))
        w,p=wilcoxon(delta,method='approx') if len(nz) else (0,1)
        comparisons.append({'a':a,'b':b,'mean_difference':np.mean(delta),'W':w,'p':p,
            'matched_rank_biserial':np.sum(np.sign(nz)*ranks)/np.sum(ranks) if len(nz) else 0})
    order=sorted(range(len(comparisons)),key=lambda i:comparisons[i]['p'])
    last=0
    for rank,i in enumerate(order):
        last=max(last,min(1,comparisons[i]['p']*(len(order)-rank)))
        comparisons[i]['p_holm']=last
    pairs=[]
    for p in sorted((ROOT/'outputs/second_rater').glob('*.json')):
        r=read(p); key=(r['case_id'],r['model_requested'])
        pairs.append((key, means[key],r['qwen_score']))
    primary=[[round(a[d]) for _,a,b in pairs] for d in DIMS]
    secondary=[[round(b[d]) for _,a,b in pairs] for d in DIMS]
    alpha={}
    for i,d in enumerate(DIMS):
        try: alpha[d]=krippendorff.alpha([primary[i],secondary[i]],level_of_measurement='ordinal')
        except ValueError: alpha[d]=None
    alpha['pooled']=krippendorff.alpha([sum(primary,[]),sum(secondary,[])],level_of_measurement='ordinal')
    response_diffs=[np.mean([b[d]-a[d] for d in DIMS]) for _,a,b in pairs]
    cluster=defaultdict(list)
    for (key,a,b),diff in zip(pairs,response_diffs): cluster[key[0]].append(diff)
    case_diffs=[np.mean(v) for v in cluster.values()]
    w,p=wilcoxon(response_diffs)
    cw,cp=wilcoxon(case_diffs)
    sensitivity=[]
    for label,a,b in [('reported',0,7),('one weak flag removed',0,6),('one strong flag added',1,7),
                      ('one weak flag added',0,8),('two weak flags removed',0,5),('two strong flags added',2,7)]:
        sensitivity.append({'scenario':label,'strong_misses':a,'weak_misses':b,
           'denominator_per_group':12,'fisher_two_sided_p':fisher_exact([[a,12-a],[b,12-b]]).pvalue})
    dates=[]
    for cid,c in cases.items():
        validity=c['artifacts'].get('certificate',{}).get('validity','') or ''
        if ' to ' in validity:
            end=validity.split(' to ')[1]
            after=[t['timestamp'] for t in c['artifacts'].get('traffic_log',[]) if t.get('timestamp','')[:10]>end]
            if after: dates.append({'case_id':cid,'tag':c['difficulty_tag'],'certificate_end':end,'later_traffic':after,
                                    'interpretation':'date ordering only; not proof of a logical contradiction or compromise'})
    expected=['scripts/deterministic_audit.py','scripts/audit_crossval.py',
              'outputs/deterministic_audit.json','scoring/audit_crossval.json']
    report={'n_cases':len(cases),'n_responses':len(records),'n_claims':len(scores),
      'tags':dict(Counter(c['difficulty_tag'] for c in cases.values())),
      'prompt_mismatches':prompt_mismatches,'models':rows,'paired_comparisons':comparisons,
      'second_rater':{'n_responses':len(pairs),'n_unique_cases':len(cluster),'rounded_ordinal_alpha':alpha,
        'mean_secondary_minus_primary':np.mean(response_diffs),'response_wilcoxon':{'W':w,'p':p},
        'case_aggregated_wilcoxon':{'W':cw,'p':cp},
        'warning':'Different units: primary claim mean versus holistic secondary score; pooling dimensions does not validate a common construct.'},
      'historical_fisher_sensitivity':sensitivity,
      'historical_case_signflip_bounds':{'affected_cases_min':4,'affected_cases_max':6,
         'two_sided_p_min':2/2**6,'two_sided_p_max':2/2**4,
         'status':'Bound from reported margins, not an item-level replication; 7 misses in 2 models over 6 paired cases.'},
      'nine_of_nine_precision_exact95':list(binomtest(9,9).proportion_ci()),
      'certificate_date_ordering':dates,
      'missing_historical_artifacts':[p for p in expected if not (ROOT/p).exists()],
      'legacy_source_matches_final_pdf':False}
    out=ROOT/'scoring/satml';out.mkdir(parents=True,exist_ok=True)
    (out/'legacy_audit.json').write_text(json.dumps(clean(report),indent=2,allow_nan=False),encoding='utf-8')
    manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
              for folder,pattern in [('cases','*.json'),('outputs/harness','*.json'),('scoring','*.json'),('paper','*.pdf')]
              for p in sorted((ROOT/folder).glob(pattern))}
    (out/'legacy_sha256.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    extension_paths=[]
    for pattern in ['outputs/satml/legacy/*.json','scripts/satml_*.py',
                    'scripts/deterministic_audit.py','scripts/validate_reconstructed_flags.py',
                    'scoring/satml/reconstructed_flag_validation.json']:
        extension_paths.extend(ROOT.glob(pattern))
    extension_manifest={str(p.relative_to(ROOT)).replace('\\','/'):
                        hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(set(extension_paths)) if p.is_file()}
    (out/'extension_sha256.json').write_text(json.dumps(extension_manifest,indent=2),encoding='utf-8')
    print(json.dumps(clean(report),indent=2,allow_nan=False))

if __name__=='__main__': main()
