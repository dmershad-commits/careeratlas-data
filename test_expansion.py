import sys,json,tempfile,unittest
from pathlib import Path
from contextlib import closing
sys.path.insert(0,str(Path(__file__).parent/'collector'))
import app,updater,country_feed
import cloud_refresh as cloud
from unittest.mock import patch
class CountryTests(unittest.TestCase):
 def sample(self):
  return dict(id='123',headline='Teacher',employer={'name':'Real School'},removed=False,webpage_url='https://arbetsformedlingen.se/platsbanken/annonser/123',application_details={'url':'http://unsafe.example'},workplace_address={'municipality':'Lund','country':'Sverige'},occupation_field={'label':'Education'},workplace_model={'label':None},publication_date='2026-10-21T10:00:00',application_deadline='2026-11-02T23:59:59')
 def test_dates_and_safe_link(self):
  row=country_feed.parse(self.sample());self.assertEqual(row['url'],'https://arbetsformedlingen.se/platsbanken/annonser/123');self.assertTrue(row['deadline'].endswith('+01:00'));self.assertEqual(country_feed.date('2026-07-01T12:00:00'),'2026-07-01T12:00:00+02:00');self.assertEqual(row['work_mode'],'unknown')
 def test_employer_migration_and_partial_retention(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
   dbpath=Path(temp)/'jobs.db';app.initialize(dbpath);app.initialize(dbpath)
   with closing(app.connect(dbpath)) as db:
    feed=next(f for f in updater.feeds() if f['board']=='sweden-jobsearch');row=country_feed.parse(self.sample());updater.apply_snapshot(db,feed,[row],'2026-10-21T12:00:00+00:00',False)
    jobs=app.list_jobs(db);self.assertEqual(jobs[0]['organization'],'Real School');self.assertEqual(jobs[0]['industry'],'Education');self.assertEqual(jobs[0]['sector'],'Not stated');self.assertEqual(jobs[0]['countries'],['Sweden'])
    db.commit()
    updater.apply_snapshot(db,feed,[],'2026-10-22T12:00:00+00:00',False);self.assertEqual(db.execute('select availability from collected_jobs').fetchone()[0],'listed')
 def test_state_restores_real_employer(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
   root=Path(temp);(root/'public').mkdir();dbpath=root/'state.db';app.initialize(dbpath)
   with closing(app.connect(dbpath)) as db:
    feed=next(f for f in updater.feeds() if f['board']=='sweden-jobsearch');updater.apply_snapshot(db,feed,[country_feed.parse(self.sample())],'2026-10-21T12:00:00+00:00',False)
   with patch.object(cloud,'ROOT',root),patch.object(app,'DB',dbpath):cloud.write_state(root/'public')
   restored=root/'restored.db'
   with patch.object(cloud,'ROOT',root),patch.object(app,'DB',restored):cloud.restore_state()
   with closing(app.connect(restored)) as db:
    job=app.list_jobs(db)[0];self.assertEqual(job['organization'],'Real School');self.assertEqual(job['industry'],'Education');self.assertEqual(job['sector'],'Not stated')
 def test_removed_and_identity(self):
  j=self.sample();j['removed']=True;self.assertIsNone(country_feed.parse(j));j['removed']=False;j['webpage_url']='https://evil.example';self.assertRaises(ValueError,country_feed.parse,j)
if __name__=='__main__':unittest.main()

