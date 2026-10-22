"""Publish only explicitly licensed data. Standard library; no paid services."""
import gzip,json,os,sys,time
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.parse import urlsplit

API='https://jobsearch.api.jobtechdev.se/search'
LICENCE='https://data.jobtechdev.se/dataservice'
def safe(url):
 try:
  u=urlsplit(url or '')
  return u.scheme=='https' and bool(u.hostname) and not u.username and not u.password
 except ValueError:return False
def normalize(j,now):
 ident=str(j.get('id',''))
 if not ident.isdigit() or j.get('removed') is not False:return None
 title=j.get('headline');org=(j.get('employer') or {}).get('name')
 if not isinstance(title,str) or not isinstance(org,str) or not title or not org:return None
 notice=f'https://arbetsformedlingen.se/platsbanken/annonser/{ident}'
 if j.get('webpage_url')!=notice:return None
 end=j.get('application_deadline')
 if end:
  # If no offset is provided, expire conservatively at the start of the date UTC.
  try:
   dt=datetime.fromisoformat(end.replace('Z','+00:00'))
   if dt.tzinfo is None:dt=datetime.fromisoformat(end[:10]).replace(tzinfo=timezone.utc)
   end=dt.isoformat()
   if dt<=datetime.fromisoformat(now):return None
  except ValueError:end=None
 addr=j.get('workplace_address') or {};country=addr.get('country') or ''
 country='Sweden' if country=='Sverige' else country
 location=', '.join(dict.fromkeys(x for x in [addr.get('city') or addr.get('municipality'),addr.get('region'),country] if x))
 url=(j.get('application_details') or {}).get('url')
 if not safe(url):url=notice
 field=(j.get('occupation_field') or {}).get('label') or 'Not classified'
 model=((j.get('workplace_model') or {}).get('label') or '').lower()
 mode='hybrid' if 'hybrid' in model else 'remote' if 'distans' in model else 'unknown'
 return dict(id='sweden-jobsearch:'+ident,title=title,organization=org,sector='Not stated',location=location,work_mode=mode,url=url,source_url=notice,posted_on=j.get('publication_date'),deadline=end,closed=False,career_level='unknown',countries=[country] if country else [],industry=field,summary=f'Occupational field: {field}. Confirm requirements and application instructions in the original notice.',availability='listed',salary=None,attribution='Swedish Public Employment Service — JobSearch (CC0)',last_seen=now,first_seen=now,reuse_license='CC0-1.0',reuse_evidence=LICENCE)
def collect():
 now=datetime.now(timezone.utc).isoformat();rows={}
 for offset in range(0,500,100):
  req=Request(API+f'?limit=100&offset={offset}&sort=pubdate-desc',headers={'User-Agent':'CareerAtlas/1.0 (public CC0 vacancy search)'})
  with urlopen(req,timeout=40) as r:page=json.load(r)
  if not isinstance(page.get('hits'),list):raise ValueError('Unexpected API response')
  for item in page['hits']:
   row=normalize(item,now)
   if row:rows[row['id']]=row
  if len(page['hits'])<100:break
  time.sleep(.3)
 if not rows:raise ValueError('No current licensed records; previous data retained')
 return dict(generated_at=now,reuse_policy='licensed-only-v1',jobs=list(rows.values()),sources=[dict(name='Swedish Public Employment Service — JobSearch',url='https://jobtechdev.se/en/products/jobsearch',enabled=True,license='CC0-1.0',last=dict(status='partial',finished_at=now,fetched=len(rows)))])
def main():
 out=Path('public');out.mkdir(exist_ok=True);data=collect()
 old=out/'licensed-jobs.json'
 if old.exists():
  previous={j['id']:j['first_seen'] for j in json.loads(old.read_text(encoding='utf-8')).get('jobs',[])}
  for j in data['jobs']:j['first_seen']=previous.get(j['id'],j['first_seen'])
 payload=json.dumps(data,ensure_ascii=False,separators=(',',':'))
 temp=out/'licensed-jobs.tmp';temp.write_text(payload,encoding='utf-8');temp.replace(old)
 (out/'jobs.json.gz').write_bytes(gzip.compress(payload.encode(),mtime=0))
 # Replace old current-state export; no historic unlicensed records carried forward.
 (out/'state.json.gz').write_bytes(gzip.compress(b'{}',mtime=0))
 (out/'link-health.json').write_text('{}',encoding='utf-8')
 status=dict(generated_at=data['generated_at'],jobs=len(data['jobs']),successful_sources=1,total_sources=1,partial_sources=['sweden-jobsearch'],failed_sources=[],reuse_policy='licensed-only-v1',run_url=f"https://github.com/{os.environ.get('GITHUB_REPOSITORY','dmershad-commits/careeratlas-data')}/actions/runs/{os.environ.get('GITHUB_RUN_ID','')}")
 (out/'status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
 if os.environ.get('EVENT_NAME')=='schedule':(out/'scheduler.json').write_text(json.dumps(dict(event='schedule',cron=os.environ.get('CRON'),**status)),encoding='utf-8')
 print(json.dumps(status))
def test():
 now='2026-10-23T00:00:00+00:00';j=dict(id='123',removed=False,headline='Example',employer={'name':'Example employer'},webpage_url='https://arbetsformedlingen.se/platsbanken/annonser/123',application_details={'url':'javascript:bad'})
 r=normalize(j,now);assert r['url']==j['webpage_url'];assert r['reuse_license']=='CC0-1.0';assert 'description' not in r
 assert normalize(dict(j,removed=True),now) is None
 assert normalize(dict(j,application_deadline='2026-01-01'),now) is None
 assert normalize(dict(j,webpage_url='https://example.org'),now) is None
 print('PASS licensed source identity, expiry, URL safety and minimal public fields')
if __name__=='__main__':test() if '--test' in sys.argv else main()
