"""Versioned, resumable model runs; no silent provider fallback or secret logging."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.request
import urllib.error
from satml_environment import load_keys

ROOT=Path(__file__).resolve().parents[1]

def digest(text): return hashlib.sha256(text.encode()).hexdigest()
def name(model): return re.sub(r'[^A-Za-z0-9._-]','-',model)

def call(url,body,headers=None,timeout=600):
    req=urllib.request.Request(url,data=json.dumps(body).encode(),headers={
        'Content-Type':'application/json',**(headers or {})})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)

def run_one(case,model,suite,outdir):
    prompt=case['task_prompt'].replace('{ARTIFACTS_JSON}',json.dumps(case['artifacts'],indent=2))
    cap=4096 if suite=='legacy' else 1536
    local=':' in model
    settings={'max_output_tokens':cap,'reasoning_effort':'medium' if not local else None,
              'temperature':0 if local else None,'seed':42 if local else None,
              'think':False if model.startswith('qwen3:') else None,
              'context_tokens':8192 if local else None}
    fingerprint=digest(json.dumps({'prompt':prompt,'model':model,'suite':suite,'settings':settings},sort_keys=True))
    dest=outdir/f"{case['case_id']}__{name(model)}.json"
    if dest.exists():
        old=json.loads(dest.read_text(encoding='utf-8'))
        if old['request_sha256']!=fingerprint: raise ValueError('Existing output has different request fingerprint')
        print('SKIP',dest.name,flush=True);return
    start=time.monotonic()
    if local:
        metadata=call('http://localhost:11434/api/show',{'model':model})
        body={'model':model,'messages':[{'role':'user','content':prompt}], 'stream':False,
              'options':{'num_predict':cap,'num_ctx':8192,'temperature':0,'seed':42}}
        if model.startswith('qwen3:'): body['think']=False
        raw=call('http://localhost:11434/api/chat',body)
        text=raw.get('message',{}).get('content','')
        served=raw.get('model',model);status=raw.get('done_reason','unknown')
        complete=bool(raw.get('done')) and status=='stop' and bool(text.strip())
        usage={k:raw.get(k) for k in ['prompt_eval_count','eval_count','total_duration']}
    else:
        body={'model':model,'input':[{'role':'user','content':prompt}], 'max_output_tokens':cap,
              'reasoning':{'effort':'medium'},'store':False}
        raw=call('https://api.openai.com/v1/responses',body,
                 {'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']})
        text='\n'.join(c.get('text','') for item in raw.get('output',[]) if item.get('type')=='message'
                       for c in item.get('content',[]) if c.get('type')=='output_text')
        served=raw.get('model');status=raw.get('status')
        complete=status=='completed' and bool(text.strip())
        usage=raw.get('usage',{});metadata=None
    result={'case_id':case['case_id'],'model_requested':model,'model_served_by':served,
      'suite':suite,'timestamp_utc':datetime.now(timezone.utc).isoformat(),
      'prompt':prompt,'prompt_sha256':digest(prompt),'case_sha256':digest(json.dumps(case,sort_keys=True)),
      'request_sha256':fingerprint,'settings':settings,'response_text':text,'complete':complete,
      'stop_reason':status,'elapsed_seconds':time.monotonic()-start,'usage':usage,
      'local_model_metadata':metadata,'raw_response':raw}
    tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(result,indent=2),encoding='utf-8');tmp.replace(dest)
    print('OK' if complete else 'INCOMPLETE',dest.name,round(result['elapsed_seconds'],1),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--models',required=True)
    ap.add_argument('--suite',choices=['legacy','probes'],default='legacy')
    ap.add_argument('--limit',type=int);ap.add_argument('--workers',type=int,default=1)
    args=ap.parse_args();load_keys()
    cases_dir=ROOT/('cases' if args.suite=='legacy' else 'cases_v2/probes')
    cases=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(cases_dir.glob('*.json'))]
    if args.limit: cases=cases[:args.limit]
    out=ROOT/'outputs/satml'/args.suite;out.mkdir(parents=True,exist_ok=True)
    failures=[]
    def job(pair):
        c,m=pair
        try: run_one(c,m,args.suite,out)
        except urllib.error.HTTPError as e:
            # No response body: provider errors may echo inputs. Status is enough to diagnose access.
            failures.append({'case':c['case_id'],'model':m,'http_status':e.code})
            print('FAILED',c['case_id'],m,'HTTP',e.code,flush=True)
        except Exception as e:
            failures.append({'case':c['case_id'],'model':m,'error_type':type(e).__name__})
            print('FAILED',c['case_id'],m,type(e).__name__,flush=True)
    pairs=[(c,m) for m in args.models.split(',') for c in cases]
    with ThreadPoolExecutor(max_workers=args.workers) as pool: list(pool.map(job,pairs))
    if failures:
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        (out/f'failures-{stamp}.log').write_text(json.dumps(failures,indent=2),encoding='utf-8')
        raise SystemExit(1)

if __name__=='__main__':main()
