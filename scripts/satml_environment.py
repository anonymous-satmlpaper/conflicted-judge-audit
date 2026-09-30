"""Inspect experiment access without printing credentials."""
import json
import os
from pathlib import Path
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]

def load_keys():
    for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip().upper(), value.strip().strip('\"\''))

def main():
    load_keys()
    report = {'credentials_present': {k: bool(os.getenv(k)) for k in
              ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']}}
    for provider, url, headers in [
        ('openai', 'https://api.openai.com/v1/models',
         {'Authorization': 'Bearer ' + os.getenv('OPENAI_API_KEY', '')}),
        ('ollama', 'http://localhost:11434/api/tags', {})]:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                data = json.load(r)
            report[provider] = sorted(x['id'] for x in data['data']) if provider == 'openai' else data
        except urllib.error.HTTPError as e:
            report[provider] = {'http_status': e.code}
        except Exception as e:
            report[provider] = {'error_type': type(e).__name__}
    out = ROOT / 'scoring/satml/environment.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
