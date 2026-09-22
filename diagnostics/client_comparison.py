import json, subprocess, tempfile, time, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shelf import parse_feed
from diagnostics.arxiv_probe import HEADERS
import argparse
parser = argparse.ArgumentParser(description='Bounded, sequential arXiv request comparison; stop the shelf first.')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
 parser.error('Report already exists; choose a new output path.')
url='https://export.arxiv.org/api/query?id_list=2308.15440v2%2C2412.16795v1&max_results=2'
ua='arxiv-shelf/1.0 (local personal PDF index)'
report={'url':url,'user_agent':ua,'cases':[]}
for i,client in enumerate(('python','wsl-curl','windows-curl','python-after-curl')):
 if i: time.sleep(3.2)
 r={'client':client,'utc':datetime.now(timezone.utc).isoformat()}
 try:
  if client.startswith('python'):
   try:
    response=urlopen(Request(url,headers={'User-Agent':ua}),timeout=35)
   except HTTPError as e: response=e
   with response:
    body=response.read()
    r.update(http_status=response.code,headers={k:response.headers.get(k) for k in HEADERS})
  else:
   executable='curl' if client=='wsl-curl' else 'curl.exe'
   version=subprocess.run([executable,'--version'],capture_output=True,text=True,timeout=10)
   r['version']=version.stdout.splitlines()[0]
   # stdout contains only response headers + body, no proxy credentials or verbose connection logs.
   result=subprocess.run([executable,'--http1.1','--max-time','35','-sS','-i','-A',ua,url],capture_output=True,timeout=40)
   data=result.stdout.replace(b'\r\n',b'\n')
   header,body=data.split(b'\n\n',1)
   # Accommodate a proxy's CONNECT response without publishing its headers.
   if b'200 Connection established' in header and body.startswith(b'HTTP/'):
    header,body=body.split(b'\n\n',1)
   lines=header.decode(errors='replace').splitlines()
   headers=dict(line.split(':',1) for line in lines[1:] if ':' in line)
   headers={k.lower():v.strip() for k,v in headers.items()}
   r.update(http_status=int(lines[0].split()[1]),headers={k:headers.get(k.lower()) for k in HEADERS},exit_code=result.returncode)
  r['body_empty']=not bool(body)
  if r['http_status']==200:
   r['returned_ids']=sorted(parse_feed(body))
 except Exception as exc:
  r['error_type']=type(exc).__name__
 report['cases'].append(r)
 print(json.dumps(r),flush=True)
 if r.get('http_status') in (403,429): break
with args.output.open('x', encoding='utf-8') as f: json.dump(report,f,indent=2);f.write('\n')
