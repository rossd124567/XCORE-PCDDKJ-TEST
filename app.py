import json, os, re, time, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html.parser import HTMLParser
HOME='https://pcddkj.com/'
HEADERS={'User-Agent':'Mozilla/5.0 XCORE-PC28-ReadOnly-Diagnostic/1.0','Accept':'text/html,application/json,*/*'}
class Scripts(HTMLParser):
 def __init__(self): super().__init__(); self.scripts=[]
 def handle_starttag(self,tag,attrs):
  if tag=='script':
   src=dict(attrs).get('src')
   if src:self.scripts.append(urllib.parse.urljoin(HOME,src))
def probe():
 result={'service':'XCORE PCDDKJ read-only diagnostic','source':HOME,'timestamp':int(time.time()),'status':'unverified','live_draw_connected':False,'prediction_connected':False}
 try:
  req=urllib.request.Request(HOME,headers=HEADERS)
  with urllib.request.urlopen(req,timeout=12) as r:
   raw=r.read(500001)
   if len(raw)>500000:raise ValueError('homepage exceeds 500KB diagnostic limit')
   html=raw.decode('utf-8','replace'); p=Scripts();p.feed(html)
   result.update(status='homepage_reachable',http_status=r.status,content_type=r.headers.get('Content-Type',''),html_chars=len(html),scripts=p.scripts[:12],endpoint_name_hints=sorted(set(re.findall(r'[\w./-]*(?:kj|history|stats|feed|miss)\.json',html,re.I)))[:20],prediction_selector_hints={x:(x in html) for x in ['pane-yuce-dx','pane-yuce-ds']})
 except Exception as e:result.update(status='homepage_error',error=f'{type(e).__name__}: {str(e)[:220]}')
 return result
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  path=urllib.parse.urlparse(self.path).path
  if path=='/': payload={'message':'XCORE PCDDKJ diagnostic service','routes':['/health','/probe'],'warning':'Read-only test; no verified draw or prediction API connected'}
  elif path=='/health':payload={'ok':True,'service':'xcore-pcddkj-diagnostic'}
  elif path=='/probe':payload=probe()
  else:
   self.send_error(404);return
  data=json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8');self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
if __name__=='__main__':
 port=int(os.getenv('PORT','8080'));print(f'Listening on {port}',flush=True);ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
