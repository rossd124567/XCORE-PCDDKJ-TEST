# -*- coding: utf-8 -*-
"""XCORE PCDDKJ read-only diagnostic API. No betting, no fabricated data."""
import json,os,re,time,urllib.request,urllib.parse,threading,copy,subprocess,sys
from http.server import BaseHTTPRequestHandler,HTTPServer
from html.parser import HTMLParser
HOME='https://pcddkj.com/'
HEADERS={'User-Agent':'Mozilla/5.0 (XCORE-PC28-ReadOnly/2.0)','Accept':'application/json,text/html,*/*'}
MAX_BYTES=700000

class PageParser(HTMLParser):
 def __init__(self):
  super().__init__();self.scripts=[];self.ids=set();self.tables=[];self.active=None;self.in_cell=False;self.cell='';self.row=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);ident=a.get('id','')
  if ident:self.ids.add(ident)
  if tag=='script' and a.get('src'):self.scripts.append(urllib.parse.urljoin(HOME,a['src']))
  if tag=='table' and self.active is not None:self.active['table_depth']+=1
  if ident in ('pane-yuce-dx','pane-yuce-ds'):self.active={'kind':ident,'table_depth':0,'rows':[],'div_depth':1}
  elif self.active is not None and tag=='div':self.active['div_depth']+=1
  if self.active is not None and self.active['table_depth']>0:
   if tag=='tr':self.row=[]
   if tag in ('td','th') and self.row is not None:self.in_cell=True;self.cell=''
 def handle_data(self,data):
  if self.in_cell:self.cell+=data
 def handle_endtag(self,tag):
  if self.active is None:return
  if tag in ('td','th') and self.in_cell:
   self.row.append(' '.join(self.cell.split()));self.in_cell=False
  if tag=='tr' and self.row is not None:
   if self.row:self.active['rows'].append(self.row)
   self.row=None
  if tag=='table' and self.active['table_depth']>0:self.active['table_depth']-=1
  if tag=='div':
   self.active['div_depth']-=1
   if self.active['div_depth']<=0:
    self.tables.append({'kind':self.active['kind'],'rows':self.active['rows'][:4]});self.active=None

def fetch(url):
 u=urllib.parse.urlparse(url)
 if u.scheme!='https' or u.hostname not in ('pcddkj.com','www.pcddkj.com') or u.username or u.password or u.port:
  raise ValueError('仅允许 HTTPS PCDDKJ 官方域名')
 req=urllib.request.Request(url,headers=HEADERS)
 with urllib.request.urlopen(req,timeout=12) as r:
  final=urllib.parse.urlparse(r.geturl())
  if final.scheme!='https' or final.hostname not in ('pcddkj.com','www.pcddkj.com'):
   raise ValueError('重定向目标不在允许域名内')
  raw=r.read(MAX_BYTES+1)
  if len(raw)>MAX_BYTES:raise ValueError('上游响应超过700KB')
  return raw.decode('utf-8','replace'),r.status,r.headers.get('Content-Type','')

def homepage():
 html,status,content_type=fetch(HOME);p=PageParser();p.feed(html)
 return html,p,status,content_type

def probe():
 out={'service':'XCORE PCDDKJ read-only diagnostic V3.1','source':HOME,'timestamp':int(time.time()),'status':'unverified','live_draw_connected':False,'prediction_connected':False}
 try:
  html,p,status,typ=homepage()
  out.update(status='homepage_reachable',http_status=status,content_type=typ,html_chars=len(html),scripts=p.scripts[:12],endpoint_name_hints=sorted(set(re.findall(r'[\w./-]*(?:kj|history|stats|feed|miss)\.json',html,re.I)))[:20],prediction_selector_hints={x:x in html for x in ('pane-yuce-dx','pane-yuce-ds')})
 except Exception as e:out.update(status='homepage_error',error=f'{type(e).__name__}: {str(e)[:220]}')
 return out

def parse_draw(obj):
 if not isinstance(obj,dict):raise ValueError('JSON根节点不是对象')
 rows=obj.get('data')
 if not isinstance(rows,list) or not rows:raise ValueError('缺少 data 开奖列表')
 result=[]
 for item in rows[:20]:
  if not isinstance(item,dict):continue
  issue=str(item.get('nbr','')).strip();number=str(item.get('number','')).strip()
  match=re.fullmatch(r'\s*([0-9])\s*[+＋]\s*([0-9])\s*[+＋]\s*([0-9])\s*=\s*(\d{1,2})\s*',number)
  if not re.fullmatch(r'\d{6,}',issue) or not match:continue
  nums=list(map(int,match.group(1,2,3)));total=int(match.group(4))
  if sum(nums)!=total or total>27:continue
  combo=('大' if total>=14 else '小')+('单' if total%2 else '双')
  declared=str(item.get('combination','')).strip()
  if declared and declared!=combo:continue
  result.append({'issue':issue,'numbers':nums,'sum':total,'combination':combo,'open_time':item.get('time')})
 if not result:raise ValueError('未找到通过期号、和值、大小单双校验的开奖结果')
 return {'latest':max(result,key=lambda x:int(x['issue'])),'recent':result,'countdown_raw':obj.get('countdown')}

def configured_json(env_name,parser=None):
 url=os.getenv(env_name,'').strip()
 if not url:return {'status':'unconfigured','message':f'尚未配置 {env_name} 完整请求 URL；不猜测地址','verified':False}
 try:
  raw,http_status,typ=fetch(url)
  obj=json.loads(raw)
  data=parser(obj) if parser else obj
  return {'status':'ok','verified':bool(parser),'source_url':url,'fetched_at':int(time.time()),'http_status':http_status,'data':data}
 except Exception as e:return {'status':'error','verified':False,'message':f'{type(e).__name__}: {str(e)[:240]}'}

def history():
 url=os.getenv('PCDDKJ_HISTORY_URL','').strip()
 if not url:return {'status':'unconfigured','verified':False,'message':'尚未配置 PCDDKJ_HISTORY_URL 完整历史接口 URL'}
 try:
  raw,_,_=fetch(url);obj=json.loads(raw)
  rows=obj if isinstance(obj,list) else obj.get('data',obj.get('rows',None)) if isinstance(obj,dict) else None
  if not isinstance(rows,list):raise ValueError('未识别历史列表结构')
  normalized=[]
  for item in rows[:100]:
   if not isinstance(item,dict):continue
   issue=str(item.get('section',item.get('nbr',''))).strip()
   nums=[item.get(f'openCode{i}') for i in (1,2,3)]
   try:nums=[int(x) for x in nums];total=int(item.get('he'))
   except (TypeError,ValueError):continue
   if not re.fullmatch(r'\d{6,}',issue) or not all(0<=x<=9 for x in nums) or sum(nums)!=total:continue
   normalized.append({'issue':issue,'numbers':nums,'sum':total,'combination':('大' if total>=14 else '小')+('单' if total%2 else '双'),'open_time':item.get('openTime')})
  if not normalized:raise ValueError('没有通过校验的历史记录')
  return {'status':'ok','verified':True,'fetched_at':int(time.time()),'data':normalized}
 except Exception as e:return {'status':'error','verified':False,'message':f'{type(e).__name__}: {str(e)[:240]}'}

def prediction(verified_draw=None):
 """Browser-rendered read-only prediction. Never claim verified on missing or mismatched issue."""
 result={'status':'unverified','verified':False,'fetched_at':int(time.time()),
         'source':HOME,'message':'预测未通过期号和方向校验'}
 try:
  from playwright.sync_api import sync_playwright
 except ImportError:
  return dict(result,status='error',message='未安装 Playwright；请使用本包 Dockerfile 部署')
 try:
  draw=verified_draw if verified_draw is not None else configured_json('PCDDKJ_DRAW_URL',parse_draw)
  if draw.get('status')!='ok' or not draw.get('verified'):
   return dict(result,message='最新开奖未通过验证，无法确定预测目标期号',draw_status=draw.get('status'))
  latest_issue=draw['data']['latest']['issue']
  expected=str(int(latest_issue)+1)
  result['latest_draw_issue']=latest_issue
  result['expected_prediction_issue']=expected
  found={}
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
   try:
    page=browser.new_page(locale='zh-CN',viewport={'width':1366,'height':900})
    page.set_default_timeout(9000)
    page.set_default_navigation_timeout(20000)
    page.goto(HOME,wait_until='domcontentloaded',timeout=20000)
    # The website's prediction tabs can be client-rendered.
    try:
     page.get_by_text('预测',exact=True).first.click(timeout=3500)
    except Exception:
     pass
    for category,selector,allowed in [('大小','#pane-yuce-dx',('大','小')),('单双','#pane-yuce-ds',('单','双'))]:
     try:
      page.get_by_text(category,exact=True).first.click(timeout=2500)
     except Exception:
      pass
     panel=page.locator(selector)
     panel.wait_for(state='attached',timeout=9000)
     rows=panel.locator('table tbody tr')
     try:
      rows.first.wait_for(state='attached',timeout=9000)
     except Exception:
      raise ValueError(f'{category}预测表无数据行')
     cells=[v.strip() for v in rows.first.locator('td').all_text_contents()]
     if len(cells)<4:raise ValueError(f'{category}表格不足4列: {cells[:5]}')
     match=re.search(r'\d{6,}',cells[0])
     if not match:raise ValueError(f'{category}预测期号无效: {cells[0][:30]}')
     issue=match.group()
     direction=cells[3]
     if direction not in allowed:raise ValueError(f'{category}预测方向无效: {direction[:30]}')
     found[category]={'issue':issue,'direction':direction,'source':'PCDDKJ rendered DOM'}
   finally:
    browser.close()
  result['predictions']=found
  if len(found)!=2:
   return dict(result,message='未同时取得大小和单双预测')
  if any(item['issue']!=expected for item in found.values()):
   return dict(result,message='预测期号与最新开奖的下一期不一致，拒绝验证')
  return dict(result,status='ok',verified=True,message='网页预测值与目标期号匹配；不代表预测准确性')
 except Exception as e:
  return dict(result,status='error',message=f'{type(e).__name__}: {str(e)[:240]}')

# V3.5: Independent draw/history and prediction workers. Browser runs in a
# subprocess with a hard deadline so Chromium cannot block the draw loop.
_CACHE_LOCK = threading.Lock()
_CACHE = {}
_FALLBACK_SLEEP = max(15, int(os.getenv('PCDDKJ_FALLBACK_SECONDS', '25')))
_COUNTDOWN_BUFFER = max(0, int(os.getenv('PCDDKJ_COUNTDOWN_BUFFER_SECONDS', '5')))
_RETRY_SLEEP = max(15, int(os.getenv('PCDDKJ_RETRY_SECONDS', '25')))
_DRAW_INTERVAL = max(5, min(60, int(os.getenv('PCDDKJ_DRAW_INTERVAL_SECONDS', '12'))))
_PREDICTION_INTERVAL = max(15, int(os.getenv('PCDDKJ_PREDICTION_INTERVAL_SECONDS', '30')))
_PREDICTION_TIMEOUT = max(15, int(os.getenv('PCDDKJ_PREDICTION_TIMEOUT_SECONDS', '45')))
_FETCHERS = {'/api/draw': lambda: configured_json('PCDDKJ_DRAW_URL', parse_draw),
             '/api/history': history, '/api/prediction': prediction, '/probe': probe}
_STARTED_AT = int(time.time())
_LAST_COMPLETE_ISSUE = None
_NEXT_CHECK_AT = 0
_SCHEDULE_REASON = 'startup'
_LAST_COUNTDOWN_SECONDS = None
_WORKER_PHASE = 'startup'
_WORKER_PHASE_AT = int(time.time())
_LAST_WORKER_ERROR = None
_LAST_WORKER_COMPLETED_AT = None
_PRED_PHASE = 'startup'
_PRED_PHASE_AT = int(time.time())
_PRED_LAST_ERROR = None
_PRED_LAST_COMPLETED_AT = None
_PRED_NEXT_CHECK_AT = 0
_LAST_DRAW_ISSUE = None
_LAST_DRAW_CHANGE_AT = 0
_DRAW_MAX_UNCHANGED = max(180, int(os.getenv('PCDDKJ_DRAW_MAX_UNCHANGED_SECONDS', '480')))

def worker_phase(name):
 global _WORKER_PHASE,_WORKER_PHASE_AT
 _WORKER_PHASE=name;_WORKER_PHASE_AT=int(time.time())

def pred_phase(name):
 global _PRED_PHASE,_PRED_PHASE_AT
 _PRED_PHASE=name;_PRED_PHASE_AT=int(time.time())

def countdown_seconds(value):
 if isinstance(value,bool) or value is None:return None
 if isinstance(value,(int,float)):seconds=int(value)
 elif isinstance(value,str):
  value=value.strip()
  if re.fullmatch(r'\d+',value):seconds=int(value)
  elif re.fullmatch(r'\d{1,2}:\d{2}(?::\d{2})?',value):
   seconds=sum(n*60**i for i,n in enumerate(reversed([int(v) for v in value.split(':')])))
  else:return None
 else:return None
 return seconds if 0<=seconds<=180 else None

def cache_set(path,payload):
 with _CACHE_LOCK:_CACHE[path]={'payload':payload,'cached_at':int(time.time())}

def draw_worker():
 global _NEXT_CHECK_AT,_SCHEDULE_REASON,_LAST_COUNTDOWN_SECONDS,_LAST_WORKER_ERROR,_LAST_WORKER_COMPLETED_AT,_LAST_DRAW_ISSUE,_LAST_DRAW_CHANGE_AT
 while True:
  worker_phase('fetch_draw')
  try:
   draw=_FETCHERS['/api/draw']()
   if draw.get('verified') is True:
    issue=draw['data']['latest']['issue']
    if issue!=_LAST_DRAW_ISSUE:
     _LAST_DRAW_ISSUE=issue;_LAST_DRAW_CHANGE_AT=int(time.time())
    elif int(time.time())-_LAST_DRAW_CHANGE_AT>_DRAW_MAX_UNCHANGED:
     draw={'status':'stale','verified':False,'message':'上游最新开奖期号长期未变化，拒绝使用旧开奖','last_draw_issue':issue}
   cache_set('/api/draw',draw)
   if draw.get('verified') is True:
    _LAST_COUNTDOWN_SECONDS=countdown_seconds(draw.get('data',{}).get('countdown_raw'))
    _LAST_WORKER_ERROR=None
    _SCHEDULE_REASON='independent_draw_poll'
   else:
    _LAST_WORKER_ERROR=draw.get('message','draw unverified')
    _SCHEDULE_REASON='draw_retry'
  except Exception as exc:
   _LAST_WORKER_ERROR=f'{type(exc).__name__}: {str(exc)[:240]}'
   cache_set('/api/draw',{'status':'error','verified':False,'message':_LAST_WORKER_ERROR})
   _SCHEDULE_REASON='draw_exception'
  _LAST_WORKER_COMPLETED_AT=int(time.time())
  _NEXT_CHECK_AT=int(time.time())+_DRAW_INTERVAL
  worker_phase('sleep')
  time.sleep(_DRAW_INTERVAL)

def browser_prediction_with_deadline(draw):
 # Child process gets a verified draw snapshot; never wait indefinitely for browser.
 command=[sys.executable,os.path.abspath(__file__),'--prediction-worker']
 result=subprocess.run(command,input=json.dumps(draw,ensure_ascii=False),text=True,
                       capture_output=True,timeout=_PREDICTION_TIMEOUT)
 if result.returncode!=0:
  raise RuntimeError(f'预测子进程退出 {result.returncode}: {result.stderr[-250:]}')
 return json.loads(result.stdout)

def prediction_worker():
 global _LAST_COMPLETE_ISSUE,_PRED_LAST_ERROR,_PRED_LAST_COMPLETED_AT,_PRED_NEXT_CHECK_AT
 while True:
  pred_phase('fetch_prediction')
  try:
   with _CACHE_LOCK:entry=copy.deepcopy(_CACHE.get('/api/draw'))
   draw=entry['payload'] if entry else None
   fresh=entry is not None and time.time()-entry['cached_at']<=max(45,_DRAW_INTERVAL*3)
   if not fresh or not draw or draw.get('verified') is not True:
    pred={'status':'waiting','verified':False,'message':'等待最新有效开奖数据'}
   else:
    pred=browser_prediction_with_deadline(draw)
   cache_set('/api/prediction',pred)
   expected=str(int(draw['data']['latest']['issue'])+1) if fresh and draw and draw.get('verified') else None
   both=pred.get('predictions',{})
   if pred.get('verified') is True and expected and all(
       both.get(k,{}).get('issue')==expected and both.get(k,{}).get('direction') in allowed
       for k,allowed in [('大小',('大','小')),('单双',('单','双'))]):
    _LAST_COMPLETE_ISSUE=expected
   _PRED_LAST_ERROR=None if pred.get('verified') else pred.get('message')
  except subprocess.TimeoutExpired:
   _PRED_LAST_ERROR=f'预测浏览器超过{_PREDICTION_TIMEOUT}秒，已终止子进程'
   cache_set('/api/prediction',{'status':'error','verified':False,'message':_PRED_LAST_ERROR})
  except Exception as exc:
   _PRED_LAST_ERROR=f'{type(exc).__name__}: {str(exc)[:240]}'
   cache_set('/api/prediction',{'status':'error','verified':False,'message':_PRED_LAST_ERROR})
  _PRED_LAST_COMPLETED_AT=int(time.time())
  _PRED_NEXT_CHECK_AT=int(time.time())+_PREDICTION_INTERVAL
  pred_phase('sleep')
  time.sleep(_PREDICTION_INTERVAL)

class Handler(BaseHTTPRequestHandler):
 def setup(self):
  super().setup()
  self.connection.settimeout(5)
 def do_GET(self):
  path=urllib.parse.urlparse(self.path).path
  if path=='/':
   payload={'message':'XCORE PCDDKJ diagnostic V3.5 independent collectors',
            'routes':['/health','/probe','/api/draw','/api/history','/api/prediction'],
            'warning':'read-only; unverified results must not be used for betting'}
  elif path=='/health':
   with _CACHE_LOCK:
    states={key:{'cached_at':value['cached_at'],
                 'status':value['payload'].get('status')}
            for key,value in _CACHE.items()}
   payload={'ok':True,'service':'xcore-pcddkj-diagnostic-v3-5',
            'uptime_seconds':int(time.time())-_STARTED_AT,
            'worker_alive':_WORKER.is_alive(),'prediction_worker_alive':_PRED_WORKER.is_alive(),'cache':states,
            'last_complete_prediction_issue':_LAST_COMPLETE_ISSUE,
            'next_upstream_check_at':_NEXT_CHECK_AT,
            'schedule_reason':_SCHEDULE_REASON,
            'last_countdown_seconds':_LAST_COUNTDOWN_SECONDS,
            'worker_phase':_WORKER_PHASE,
            'worker_phase_seconds':int(time.time())-_WORKER_PHASE_AT,
            'last_worker_completed_at':_LAST_WORKER_COMPLETED_AT,
            'last_worker_error':_LAST_WORKER_ERROR,
            'worker_stalled':(_WORKER_PHASE=='fetch_draw' and int(time.time())-_WORKER_PHASE_AT>120),
            'prediction_phase':_PRED_PHASE,'prediction_phase_seconds':int(time.time())-_PRED_PHASE_AT,
            'prediction_last_error':_PRED_LAST_ERROR,'prediction_last_completed_at':_PRED_LAST_COMPLETED_AT,
            'prediction_next_check_at':_PRED_NEXT_CHECK_AT,
            'last_draw_issue':_LAST_DRAW_ISSUE,'last_draw_change_at':_LAST_DRAW_CHANGE_AT}
  elif path in _FETCHERS:
   with _CACHE_LOCK:
    entry=copy.deepcopy(_CACHE.get(path))
   if entry is None:
    payload={'status':'loading','verified':False,
             'message':'后台首次采集中，请稍后重试'}
   else:
    payload=entry['payload']
    age=int(time.time())-entry['cached_at']
    # Reject stale snapshots even when their original status was ok.
    if age > 420:
     payload={'status':'stale','verified':False,
              'message':'后台数据已过期，等待采集恢复',
              'last_cached_at':entry['cached_at']}
  else:
   self.send_error(404);return
  data=json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8')
  try:
   self.send_response(200)
   self.send_header('Content-Type','application/json; charset=utf-8')
   self.send_header('Cache-Control','no-store')
   self.send_header('Content-Length',str(len(data)))
   self.end_headers()
   self.wfile.write(data)
  except (BrokenPipeError,ConnectionResetError):
   pass

if __name__=='__main__' and '--prediction-worker' in sys.argv:
 try:
  draw=json.loads(sys.stdin.read())
  print(json.dumps(prediction(verified_draw=draw),ensure_ascii=False))
 except Exception as exc:
  print(f'{type(exc).__name__}: {exc}',file=sys.stderr)
  sys.exit(1)
 sys.exit(0)

if __name__=='__main__':
 port=int(os.getenv('PORT','8080'))
 _WORKER=threading.Thread(target=draw_worker,name='draw-refresh',daemon=True)
 _PRED_WORKER=threading.Thread(target=prediction_worker,name='prediction-refresh',daemon=True)
 _WORKER.start()
 _PRED_WORKER.start()
 print(f'XCORE read-only V3.5 independent collectors listening on {port}',flush=True)
 HTTPServer(('0.0.0.0',port),Handler).serve_forever()
