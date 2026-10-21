"""Install verified Testlio public Greenhouse feed; idempotent, no network."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'runtime')
path = root / 'collector/data/feeds.json'
feeds = json.loads(path.read_text(encoding='utf-8-sig'))
entry = dict(board='testlio', name='Testlio', sector='Private', enabled=True,
    official_url='https://www.testlio.com/careers',
    source_url='https://job-boards.greenhouse.io/testlio',
    relationship_checked_on='2026-10-21', industry='Software testing and quality assurance',
    relationship_evidence='Official careers HTML embeds https://boards.greenhouse.io/embed/job_board/js?for=testlio. Documented public Greenhouse Job Board GET API; no authentication. Mixed employee and freelance board; future-role pools excluded.',
    coverage='Published employee and freelance opportunities; geographic, equipment and on-site requirements apply.')
feeds = [f for f in feeds if f['board'] != 'testlio'] + [entry]
path.write_text(json.dumps(feeds, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
path = root / 'collector/updater.py'
text = path.read_text(encoding='utf-8-sig')
replacements = [
    ('        url=j.get("absolute_url","")',
     '        if board=="testlio" and re.search(r"\\bfuture roles?\\b|\\btalent (?:pool|community)\\b|\\bexpression of interest\\b",title,re.I): continue\n        url=j.get("absolute_url","")'),
    ('        mode=source_adapters.mode(location)',
     '        mode=source_adapters.mode(location)\n        if board=="testlio" and re.search(r"\\bon[ -]site\\b|\\bvisit\\b.*\\bairport\\b",title,re.I): mode="onsite"')]
for old,new in replacements:
    if new in text: continue
    if old not in text: raise RuntimeError('Testlio patch target changed: '+old)
    text=text.replace(old,new,1)
path.write_text(text,encoding='utf-8')
(root/'test_freelance.py').write_text((Path(__file__).parent/'test_freelance.py').read_text(encoding='utf-8'),encoding='utf-8')
print('Enabled Testlio published opportunities with future-pool exclusion and on-site override.')
