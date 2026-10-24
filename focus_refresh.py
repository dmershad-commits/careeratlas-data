"""Bounded official-source Bangladesh/remote jobs and scholarship checks. No accounts."""
import argparse, concurrent.futures, hashlib, html, json, os, re, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parent
UTC=timezone.utc
BD=timezone(timedelta(hours=6))
BRAC='https://er-api.brac.net/api/v1/job/public/job-posts/?limit=100'
CANONICAL='https://boards-api.greenhouse.io/v1/boards/canonical/jobs?content=true'
ALLOWED={'er-api.brac.net','boards-api.greenhouse.io','careers.brac.net','job-boards.greenhouse.io','canonical.com','www.ox.ac.uk','scholarships.unimelb.edu.au','erasmus-plus.ec.europa.eu'}

def fetch(url):
    if urlparse(url).scheme!='https' or urlparse(url).hostname not in ALLOWED: raise ValueError('Unapproved source')
    req=Request(url,headers={'User-Agent':'CareerAtlas-public-information/1.0 (+https://careeratlas.work/editorial.html)','Accept':'application/json,text/html'})
    with urlopen(req,timeout=35) as r:
        if urlparse(r.url).hostname not in ALLOWED:raise ValueError('Unapproved redirect')
        body=r.read(8_000_001)
        if len(body)>8_000_000:raise ValueError('Response too large')
        return body.decode('utf-8')

class Text(HTMLParser):
    def __init__(self):super().__init__();self.skip=0;self.parts=[]
    def handle_starttag(self,t,a):
        if t in ('script','style','noscript'):self.skip+=1
    def handle_endtag(self,t):
        if t in ('script','style','noscript'):self.skip=max(0,self.skip-1)
    def handle_data(self,d):
        if not self.skip:self.parts.append(d)
def clean(s):
    p=Text();p.feed(html.unescape(s or ''));return re.sub(r'\s+',' ',' '.join(p.parts)).strip()
def signature(body):return hashlib.sha256(clean(body).encode()).hexdigest()
def active(deadline,now):
    if not deadline:return True
    try:return datetime.fromisoformat(deadline.replace('Z','+00:00'))>now
    except (ValueError,TypeError):return False
def base(id,title,org,url,location,mode,now):
    return dict(id=id,title=title,organization=org,url=url,source_url=url,location=location,work_mode=mode,countries=['Bangladesh'] if org=='BRAC' else [],sector='NGO' if org=='BRAC' else 'Private',industry='Humanitarian and international development' if org=='BRAC' else 'Technology',career_level='unknown',salary=None,availability='listed',closed=False,review_mode='feed',attribution=org+' — official public vacancy feed',first_seen=now.isoformat(),last_seen=now.isoformat(),checked=now.isoformat(),deadline=None,posted_on=None)
def brac_rows(data,now):
    if not isinstance(data.get('results'),list):raise ValueError('BRAC schema changed')
    if data.get('next'):raise ValueError('BRAC result limit reached; coverage needs review')
    jobs=[]
    for r in data['results']:
        if r.get('status')!='Live' or r.get('is_external_job') is not True:continue
        # Retain only explicitly Bangladesh-national opportunities; never infer nationality from name.
        alltext=clean(' '.join(str(v) for v in r.values())).lower()
        if not re.search(r'bangladeshi nationals? only',alltext):continue
        try:deadline=datetime.fromisoformat(r['application_deadline']).replace(tzinfo=BD).isoformat()
        except (KeyError,ValueError,TypeError):continue
        if not active(deadline,now):continue
        slug=r.get('slug','')
        if not re.fullmatch(r'[a-zA-Z0-9-]+',slug):continue
        title=clean(r['job_title']);location=clean(r.get('job_location_details')) or 'Bangladesh — confirm duty station'
        j=base('brac-live:'+str(r['id']),title,'BRAC','https://careers.brac.net/jobs/'+slug+'?bulk=false',location,'onsite',now)
        j.update(deadline=deadline,deadline_raw=r['application_deadline']+' Bangladesh time; conservatively expires at start of date',posted_on=r.get('published_date'),summary='Bangladeshi nationals only. Public external vacancy. Confirm qualifications, experience, duty station and all conditions in the original employer notice; no individual eligibility assessment.',eligibility='Bangladeshi nationals only; role-specific qualifications apply.')
        jobs.append(j)
    return sorted(jobs,key=lambda j:(j['deadline'],j['id']))
def canonical_rows(data,now):
    if not isinstance(data.get('jobs'),list):raise ValueError('Canonical schema changed')
    jobs=[]
    for r in data['jobs']:
        location=r.get('location',{}).get('name','')
        if not re.search(r'home based\s*-\s*worldwide',location,re.I):continue
        url=r.get('absolute_url','')
        if urlparse(url).hostname not in {'job-boards.greenhouse.io','boards.greenhouse.io','canonical.com'}:continue
        # Feed presence establishes listing only; no invented deadline, salary or sponsorship.
        j=base('canonical-live:'+str(r['id']),r['title'],'Canonical',url,location,'remote',now)
        j.update(summary='Employer lists worldwide home-based work. Confirm role-specific qualifications, local hiring eligibility, work authorization, travel and sponsorship with Canonical. Worldwide wording does not guarantee eligibility.',eligibility='Worldwide location stated by employer; local hiring and authorization conditions still apply.',deadline_raw='Not stated in the public feed')
        jobs.append(j)
    return sorted(jobs,key=lambda j:j['id'])
def check_scholarships(seeds,now,fetcher=fetch):
    good=[];issues=[]
    for seed in seeds:
        r=dict(seed); expected=r.pop('evidence_sha256');review=r.get('review_after')
        if (r.get('deadline_date') and r['deadline_date']<=now.date().isoformat()) or (review and review<=now.date().isoformat()):
            issues.append({'source':r['provider'],'status':'deadline passed or review due'});continue
        try:
            if signature(fetcher(r['source_url']))!=expected:raise ValueError('Official content changed; editorial review required')
            r['checked']=now.date().isoformat();r['source_checked_at']=now.isoformat();r['check_method']='Official page content unchanged from human-reviewed baseline; programme deadlines still vary.';good.append(r)
        except Exception:issues.append({'source':r['provider'],'status':'Unavailable or changed; withheld pending review'})
    return good,issues
def pick(rows,previous,limit,now):
    valid={r['id']:r for r in rows if active(r.get('deadline'),now)}
    retained=[]
    for r in previous:
        if r['id'] in valid:
            current=valid.pop(r['id'])
            if r.get('first_seen'):current['first_seen']=r['first_seen']
            retained.append(current)
    return (retained+list(valid.values()))[:limit]
def main():
    now=datetime.now(UTC);public=ROOT/'public';public.mkdir(exist_ok=True)
    path=public/'focus.json';old=json.loads(path.read_text(encoding='utf8')) if path.exists() else {}
    sources=[];groups={}
    for key,url,parser in [('bangladesh',BRAC,brac_rows),('remote',CANONICAL,canonical_rows)]:
        try:
            rows=parser(json.loads(fetch(url)),now)
            if not rows:raise ValueError('No eligible current records')
            # Keep the owner's original reviewed selections while still present and current.
            originals={'bangladesh':['brac-live:3080','brac-live:3084'],'remote':['canonical-live:3290946','canonical-live:6635593']}[key]
            prior_by_id={r['id']:r for r in old.get(key,[])}
            prior=[prior_by_id.get(id,{'id':id}) for id in originals]+[r for r in old.get(key,[]) if r['id'] not in originals]
            groups[key]=pick(rows,prior,4,now)
            sources.append(dict(name=key,url=url,status='ok',eligible_count=len(rows),checked_at=now.isoformat()))
        except Exception:
            # Never relabel failed requests as successful checks or show old jobs as current.
            groups[key]=[];sources.append(dict(name=key,url=url,status='failed — current selection withheld',checked_at=now.isoformat()))
    seeds=json.loads((ROOT/'focus-scholarships.json').read_text(encoding='utf8'))
    scholarships,issues=check_scholarships(seeds,now)
    data=dict(schema_version=1,generated_at=now.isoformat(),schedule='02:00 and 14:00 UTC (08:00 and 20:00 Asia/Dhaka); provider delays possible',run_url='https://github.com/'+os.environ.get('GITHUB_REPOSITORY','dmershad-commits/careeratlas-data')+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID','local-test'),event=os.environ.get('GITHUB_EVENT_NAME','local-test'),**groups,scholarships=scholarships,sources=sources,scholarship_issues=issues,managed_scholarship_ids=[r['id'] for r in seeds],disclaimer='Independent information sharing only. No employment, admission, funding, sponsorship or visa is promised. Apply through original sources.')
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'bangladesh':len(groups['bangladesh']),'remote':len(groups['remote']),'scholarships':len(scholarships),'source_status':sources,'scholarship_issues':issues}))
if __name__=='__main__':main()
