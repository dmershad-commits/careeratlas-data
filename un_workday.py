"""Public UN employer search listings; no applications, logins or full-text copying."""
import json,re,time
from urllib.request import Request
from source_adapters import Reader,record,MAX_BYTES
CONFIG={'unhcr':('unhcr.wd3.myworkdayjobs.com','unhcr','External'),'wfp':('wfp.wd3.myworkdayjobs.com','wfp','job_openings')}
BASES={k:f'https://{v[0]}/{v[2]}' for k,v in CONFIG.items()}
def parse_page(payload,board):
    if type(payload.get('total')) is not int or not 0<=payload['total']<=5000 or not isinstance(payload.get('jobPostings'),list):raise ValueError('Invalid public Workday search response')
    host,tenant,site=CONFIG[board];rows=[];paths=[]
    for job in payload['jobPostings']:
        path=job.get('externalPath','');title=job.get('title');location=job.get('locationsText') or 'Not stated'
        if not isinstance(title,str) or not title.strip() or not isinstance(location,str) or not re.fullmatch(r'/job/[A-Za-z0-9_/%.-]+',path) or '..' in path or '%' in path:raise ValueError('Unexpected public vacancy identity')
        paths.append(path)
        # Talent pipelines and rosters are not advertised current vacancies.
        if re.search(r'\broster\b|\btalent (?:pool|community|pipeline)\b|\bexpression of interest\b',title,re.I):continue
        kind='Volunteer assignment; not a salaried staff vacancy. ' if re.search(r'\bvolunteer\b',title,re.I) else ''
        rows.append(record(path,title,location,f'https://{host}/{site}{path}',kind+f'Summary: {title}. Location: {location}. Published in the employer public recruitment portal. Read the original notice for requirements, contract, closing date and application instructions.'))
    if len(set(paths))!=len(paths):raise ValueError('Repeated vacancy within page')
    return rows,paths,payload['total']
def collect(board):
    host,tenant,site=CONFIG[board];reader=Reader(BASES[board]+'/');reader.check_robots()
    endpoint=f'https://{host}/wday/cxs/{tenant}/{site}/jobs'
    if reader.robots and not reader.robots.can_fetch('AtlasPrivateJobs',endpoint):raise ValueError('Public search denied by robots policy')
    rows=[];seen=set();expected=None;offset=0
    for _ in range(250):
        if time.monotonic()-reader.started>300:raise ValueError('Public search time limit')
        time.sleep(.4)
        request=Request(endpoint,data=json.dumps({'appliedFacets':{},'limit':20,'offset':offset,'searchText':''}).encode(),headers={'Content-Type':'application/json','Accept':'application/json','User-Agent':'AtlasPrivateJobs/4.0 (public vacancy summaries)'})
        with reader.opener.open(request,timeout=25) as response:
            raw=response.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:raise ValueError('Oversized public search response')
        batch,paths,total=parse_page(json.loads(raw),board)
        if expected is None:expected=total
        # Workday returns total=0 on continuation pages; first page owns the count.
        if (total not in (0,expected) if offset else total!=expected) or seen.intersection(paths):raise ValueError('Public listing changed during pagination; previous snapshot retained')
        seen.update(paths);rows.extend(batch);offset+=len(paths)
        if offset==expected:return {'atlas_rows':rows,'total':len(rows),'complete':True}
        if not paths or offset>expected:raise ValueError('Incomplete public search snapshot')
    raise ValueError('Public search pagination limit')
