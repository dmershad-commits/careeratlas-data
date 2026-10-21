"""Free, bounded public JobSearch API; CC0 data, factual summaries only."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
from source_adapters import Reader,record
BASE='https://jobsearch.api.jobtechdev.se/search'
def https(value):
    p=urlsplit(value or '')
    return bool(p.scheme=='https' and p.hostname and not p.username)
def date(value):
    if not value:return None
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    if d.tzinfo is None:d=d.replace(tzinfo=ZoneInfo('Europe/Stockholm'))
    return d.isoformat()
def parse(j):
    ident=str(j.get('id',''));title=j.get('headline');employer=(j.get('employer') or {}).get('name')
    if not ident.isdigit() or not isinstance(title,str) or not isinstance(employer,str) or not employer.strip():raise ValueError('Invalid Swedish job identity')
    if j.get('removed') is not False:return None
    notice=j.get('webpage_url')
    if notice!=f'https://arbetsformedlingen.se/platsbanken/annonser/{ident}':raise ValueError('Unexpected official notice URL')
    url=(j.get('application_details') or {}).get('url')
    if not https(url):url=notice
    address=j.get('workplace_address') or {}
    country=address.get('country') or 'Not stated'
    if country=='Sverige':country='Sweden'
    location=', '.join(dict.fromkeys(x for x in (address.get('city') or address.get('municipality'),address.get('region'),country) if x))
    industry=(j.get('occupation_field') or {}).get('label') or 'Not stated'
    summary=f'Summary: {title} at {employer}. {location}. Occupational field: {industry}. Source: Swedish Public Employment Service (CC0). Read the original notice for requirements.'
    deadline=date(j.get('application_deadline'))
    r=record(ident,title,location,url,summary,deadline=deadline,raw=j.get('application_deadline'),posted=(date(j.get('publication_date')) or '')[:10] or None)
    r.update(employer_name=employer,job_industry=industry,employer_sector='Not stated',source_updated_at=date(j.get('publication_date')))
    model=(j.get('workplace_model') or {}).get('label') or ''
    model=model.lower()
    r['work_mode']='remote' if 'distans' in model and 'hybrid' not in model else 'hybrid' if 'hybrid' in model else 'onsite' if model=='arbete på plats' else 'unknown'
    return r

def collect():
    reader=Reader(BASE);rows={}
    for offset in range(0,500,100):
        payload=json.loads(reader.get(BASE+f'?limit=100&offset={offset}&sort=pubdate-desc'))
        if not isinstance(payload.get('hits'),list) or not isinstance(payload.get('total',{}).get('value'),int):raise ValueError('Invalid JobSearch page')
        for job in payload['hits']:
            row=parse(job)
            if row:rows[row['external_id']]=row
        if len(payload['hits'])<100:break
    if not rows:raise ValueError('Empty JobSearch result; retain previous snapshot')
    return {'atlas_rows':list(rows.values()),'total':len(rows),'complete':False,'partial_reason':'Newest 500 advertised jobs, bounded country feed; not complete national coverage. Unseen jobs retained and deadline checked.'}


