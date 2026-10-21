"""Idempotently install verified public UN employer feeds into an unpacked runtime."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def install(runtime):
 runtime=Path(runtime);collector=runtime/'collector'
 (collector/'un_workday.py').write_text((ROOT/'un_workday.py').read_text(encoding='utf-8'),encoding='utf-8')
 p=collector/'public_feeds.py';s=p.read_text(encoding='utf-8')
 if 'import un_workday' not in s:
  s=s.replace('def nonvacancy(title):','import un_workday\nBASES.update(un_workday.BASES)\n\ndef nonvacancy(title):')
  s=s.replace('def collect(board):','def collect(board):\n    if board in un_workday.BASES:return un_workday.collect(board)')
  p.write_text(s,encoding='utf-8')
 p=collector/'data'/'feeds.json';feeds=json.loads(p.read_text(encoding='utf-8'))
 for board,name,official,source in [('unhcr','UNHCR','https://www.unhcr.org/get-involved/work-us/careers-unhcr/how-apply','https://unhcr.wd3.myworkdayjobs.com/External'),('wfp','World Food Programme','https://www.wfp.org/careers','https://wfp.wd3.myworkdayjobs.com/job_openings')]:
  item=dict(board=board,name=name,sector='UN',industry='Humanitarian and international development',official_url=official,source_url=source,relationship_evidence=f'Official careers page {official} links the employer Workday recruitment portal. Public external search and robots rules checked 2026-10-21; only public factual summaries and original links retained.',relationship_checked_on='2026-10-21',enabled=True,coverage='Public external listings only; talent rosters excluded. Deadline, salary and complete eligibility require original employer notice. No authenticated or internal vacancies.')
  if not any(f['board']==board for f in feeds):feeds.append(item)
 p.write_text(json.dumps(feeds,indent=2,ensure_ascii=False),encoding='utf-8')
if __name__=='__main__':
 import sys
 install(sys.argv[1] if len(sys.argv)>1 else 'runtime')
