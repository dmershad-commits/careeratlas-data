"""Add reviewed employer and country feeds after archive extraction. Idempotent."""
import json,re,sys
from pathlib import Path
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else 'runtime')
def patch(path,old,new):
    s=path.read_text(encoding='utf-8-sig')
    if new in s:return
    if old=='def collect(board):' and 'from country_feed import collect as country_collect' in s:return
    if old not in s:raise RuntimeError(f'Patch target changed: {path}')
    path.write_text(s.replace(old,new,1),encoding='utf-8')
feeds=ROOT/'collector/data/feeds.json'
items=json.loads(feeds.read_text(encoding='utf-8-sig'))
additions=[
 dict(board='aecom',name='AECOM',sector='Private',official_url='https://aecom.com/careers/',source_url='https://careers.smartrecruiters.com/AECOM2',relationship_evidence='Official aecom.com/careers/graduates-and-early-careers/ links smrtr.io/cmBrR, which redirects to join.smartrecruiters.com/AECOM2. Public Posting API company identifier AECOM2 verified.',industry='Engineering and infrastructure'),
 dict(board='edc',name='Education Development Center',sector='NGO',official_url='https://edc.org/about/careers/',source_url='https://careers.smartrecruiters.com/EducationDevelopmentCenter',relationship_evidence='Official edc.org/about/careers/ Open Roles links directly to careers.smartrecruiters.com/EducationDevelopmentCenter.',industry='Education and international development'),
 dict(board='sweden-jobsearch',name='Swedish Public Employment Service — JobSearch',sector='Not stated',official_url='https://jobtechdev.se/en/products/jobsearch',source_url='https://jobsearch.api.jobtechdev.se/',relationship_evidence='Official JobTech JobSearch open API; CC0 advertisements. Employer name preserved per job. Newest 500 only, not exhaustive coverage.',industry='Multiple sectors',coverage='Sweden and advertised overseas roles; newest 500, partial coverage')]
for f in additions:
    f.update(enabled=True,relationship_checked_on='2026-10-21')
    items=[i for i in items if i['board']!=f['board']];items.append(f)
feeds.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=ROOT/'collector/public_feeds.py'
patch(p,'BASES={k:', 'SMART.update({"aecom":"AECOM2","edc":"EducationDevelopmentCenter"})\nBASES={k:')
patch(p,'def collect(board):','BASES["sweden-jobsearch"]="https://jobsearch.api.jobtechdev.se/search"\n\ndef collect(board):\n    if board=="sweden-jobsearch":\n        from country_feed import collect as country_collect\n        return country_collect()')
p=ROOT/'collector/updater.py'
patch(p,'{"unicef","unesco"}', '{"unicef","unesco","sweden-jobsearch"}')
patch(p,'            ids.append(jid)','            db.execute("UPDATE jobs SET employer_name=?,job_industry=?,employer_sector=? WHERE id=?",(j.get("employer_name"),j.get("job_industry"),j.get("employer_sector"),jid))\n            ids.append(jid)')
p=ROOT/'collector/app.py'
patch(p,'        db.commit()','        for column in ("employer_name","job_industry","employer_sector"):\n            if column not in {r[1] for r in db.execute("PRAGMA table_info(jobs)")}:\n                db.execute(f"ALTER TABLE jobs ADD COLUMN {column} TEXT")\n        db.commit()')
patch(p,'        j=dict(row)','        j=dict(row)\n        if j.get("employer_name"):\n            j["organization"]=j["employer_name"]\n            j["sector"]=j.get("employer_sector") or "Not stated"')
patch(p,'        j.update(facets.classify(j))','        j.update(facets.classify(j))\n        if j.get("job_industry"):j["industry"]=j["job_industry"]')
(ROOT/'collector/country_feed.py').write_text((Path(__file__).parent/'country_feed.py').read_text(encoding='utf-8-sig'),encoding='utf-8')
print('Enabled AECOM, EDC and bounded Sweden JobSearch; employer attribution preserved.')
