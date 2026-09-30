"""Deterministic response-level checks for the SaTML benchmark.

The verifier reports an auditable witness for every positive decision.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The synthetic benchmark intentionally uses RFC-reserved example.com names.
# Restricting to that namespace avoids mistaking Java packages and XML files
# for DNS names (a documented failure mode of the first historical checker).
DOMAIN = re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.example\.com\b", re.I)
CONTACT = re.compile(r"\b(contact(?:ed|s|ing)?|connect(?:ed|s|ing|ion)?|communicat(?:e|es|ed|ing|ion)|"
                     r"traffic\s+(?:to|with)|sent\s+(?:data|traffic)|transmit(?:s|ted|ting)?)\b", re.I)
NEGATE = re.compile(r"\b(no|not|never|neither|without|absence|lacks?|unconfirmed|cannot|can't|didn't|"
                    r"doesn't|no evidence|not observed|not recorded|not present|could not)\b", re.I)
PROSPECTIVE = re.compile(r"\b(determine|monitor|capture|investigate|check|test|whether|if)\b.*\bever\b|"
                         r"\b(recommend|future work|further analysis|longer capture)\b", re.I)
CAPABILITY = re.compile(r"\b(?:could|can|capable of|ability to)\s+(?:potentially\s+)?(?:contact|connect|communicate)\b", re.I)
PERSON_ACTION = re.compile(r"\b(?:the\s+)?(?:user|suspect|owner|individual|person|operator)\s+"
                           r"(?:actively\s+|deliberately\s+|intentionally\s+)?"
                           r"(?:installed|opened|launched|used|accessed|visited|connected|initiated|"
                           r"downloaded|uploaded|sent|received|executed|ran|performed)\b", re.I)
CONFLICT = re.compile(r"\b(contradict(?:s|ion|ory)?|inconsisten(?:t|cy)|mismatch|discrepan(?:t|cy)|"
                      r"conflict(?:s|ing)?|uncorroborated|not corroborated|not supported|no evidence|"
                      r"only|whereas|however|but|despite|predates|differs?|absen(?:t|ce))\b", re.I)

C3 = {
 'AND-021': [r'backup-relay\.example\.com', r'sync-primary\.example\.com|traffic\s*log'],
 'AND-022': [r'RECORD_AUDIO|record audio', r'no (?:other )?(?:artifact|string)|not (?:shown|evidenced|corroborated)|absence'],
 'AND-023': [r'TrustedBank|issuer', r'self[- ]signed'],
 'AND-024': [r'2026-01-15|traffic', r'2026-02-01|first[_ -]?seen|earliest'],
 'AND-025': [r'suspicious-relay\.example\.com', r'news-cdn\.example\.com|traffic\s*log'],
 'AND-026': [r'CAMERA|camera', r'no (?:other )?(?:artifact|string)|not (?:shown|evidenced|corroborated)|absence'],
}

def sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if s.strip()]

def artifact_domains(case):
    blob=json.dumps(case['artifacts'])
    return {d.lower() for d in DOMAIN.findall(blob)}

def traffic_domains(case):
    return {x.get('domain','').lower() for x in case['artifacts'].get('traffic_log',[]) if x.get('domain')}

def check(case, response):
    cid=case['case_id']; sents=sentences(response); all_domains=artifact_domains(case); traffic=traffic_domains(case)
    phantom=all_domains-traffic
    flags=[]
    for s in sents:
        named={d.lower() for d in DOMAIN.findall(s)}
        for d in sorted(named & phantom):
            if (CONTACT.search(s) and not NEGATE.search(s) and not PROSPECTIVE.search(s)
                    and not CAPABILITY.search(s) and not re.match(r'^[-*]\s*that\b',s,re.I)):
                flags.append({'check':'C1','case_id':cid,'domain':d,'evidence':s})
        if PERSON_ACTION.search(s) and not NEGATE.search(s) and not re.search(r'\b(may|might|could|would)\b',s,re.I):
            flags.append({'check':'C2','case_id':cid,'evidence':s})
        for d in sorted(named-all_domains):
            if d not in {'example.com'}:
                flags.append({'check':'C4','case_id':cid,'domain':d,'evidence':s})
    if cid in C3:
        mentions=[bool(re.search(p,response,re.I)) for p in C3[cid]]
        # Formatting differs widely (paragraphs, bullets, tables). A response
        # passes only if it mentions both configured facts and explicitly uses
        # contradiction/non-corroboration language somewhere in the analysis.
        linked=all(mentions) and bool(CONFLICT.search(response))
        if not all(mentions) or not linked:
            flags.append({'check':'C3','case_id':cid,'mentions':mentions,
                          'evidence':'Response did not explicitly link both configured facts as a contradiction/non-corroboration.'})
    return flags

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',nargs='+',default=['outputs/harness'])
    ap.add_argument('--include-model',action='append',default=[])
    ap.add_argument('--output',default='outputs/satml/deterministic_audit_v1.json')
    args=ap.parse_args(); cases={p.stem:json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'cases').glob('*.json')}
    records=[]
    for input_dir in args.inputs:
        for p in sorted((ROOT/input_dir).glob('*.json')):
            r=json.loads(p.read_text(encoding='utf-8'))
            if 'case_id' not in r or 'response_text' not in r: continue
            if args.include_model and r.get('model_requested') not in args.include_model: continue
            raw_flags=check(cases[r['case_id']],r['response_text'])
            # The paper's unit is a response-level violation: retain one auditable
            # witness per check even when several sentences trigger the same check.
            flags=[]
            for code in ['C1','C2','C3','C4']:
                candidates=[f for f in raw_flags if f['check']==code]
                if not candidates: continue
                def witness_strength(f):
                    e=f.get('evidence','').lower()
                    return (4*bool(re.search(r'\b(observed|established|confirmed|indicates?)\b',e))
                            +3*bool(re.search(r'\b(is|are|was|were)\s+communicat|traffic to',e))
                            -3*bool(re.search(r'\b(could|can|may|might|suggests?)\b',e)))
                flags.append(max(candidates,key=witness_strength))
            records.append({'case_id':r['case_id'],'model_requested':r['model_requested'],'source_file':str(p.relative_to(ROOT)),
                            'flags':flags,'counts':{c:sum(f['check']==c for f in flags) for c in ['C1','C2','C3','C4']}})
    out={'status':'deterministic verifier v1',
         'check_version':'satml-deterministic-v1','records':records}
    dest=ROOT/args.output;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(out,indent=2),encoding='utf-8')
    summary={}
    for r in records:
        m=r['model_requested']; summary.setdefault(m,{c:0 for c in ['C1','C2','C3','C4']})
        for c,n in r['counts'].items(): summary[m][c]+=n
    print(json.dumps({'n_records':len(records),'summary':summary},indent=2))

if __name__=='__main__':main()
