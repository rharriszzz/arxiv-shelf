import gzip,json,time,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shelf import parse_feed
from diagnostics.arxiv_probe import HEADERS
import argparse
parser = argparse.ArgumentParser(description='Bounded, sequential arXiv request comparison; stop the shelf first.')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
 parser.error('Report already exists; choose a new output path.')
url='https://export.arxiv.org/api/query?id_list=2412.16795v1%2C2308.15440v2&max_results=2'
report={'url':url,'cases':[]}
for i,(label,extra) in enumerate([('baseline',{}),('accept-any',{'Accept':'*/*'}),('accept-gzip',{'Accept-Encoding':'gzip'})]):
 if i:time.sleep(3.2)
 r={'label':label,'extra_headers':extra,'utc':datetime.now(timezone.utc).isoformat()}
 try:
  try:response=urlopen(Request(url,headers={'User-Agent':'arxiv-shelf/1.0 (local personal PDF index)',**extra}),timeout=35)
  except HTTPError as e:response=e
  with response:
   body=response.read();r.update(http_status=response.code,headers={h:response.headers.get(h) for h in (*HEADERS,'Content-Encoding')},body_empty=not bool(body))
   if response.code==200:
    if response.headers.get('Content-Encoding')=='gzip':body=gzip.decompress(body)
    r['returned_ids']=sorted(parse_feed(body))
 except Exception as e:r['error_type']=type(e).__name__
 report['cases'].append(r);print(json.dumps(r),flush=True)
 if r.get('http_status') in (403,429):break
with args.output.open('x', encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
