import sys,unittest,json,tempfile,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'collector'))
import un_workday
from add_un_sources import install
class Tests(unittest.TestCase):
 def payload(self,title='Protection Officer',path='/job/Dhaka/Protection-Officer_JR123'):
  return {'total':1,'jobPostings':[{'title':title,'externalPath':path,'locationsText':'Dhaka, Bangladesh'}]}
 def test_summary(self):
  rows,ids,total=un_workday.parse_page(self.payload(),'unhcr');self.assertEqual(total,1);self.assertEqual(rows[0]['deadline'],None);self.assertTrue(rows[0]['url'].startswith('https://unhcr.wd3.myworkdayjobs.com/External/job/'));self.assertNotIn('postedOn',rows[0])
 def test_roster_exclusion(self):self.assertEqual(un_workday.parse_page(self.payload('Driver Roster'),'wfp')[0],[])
 def test_volunteer_disclosure(self):self.assertIn('not a salaried staff vacancy',un_workday.parse_page(self.payload('UN Volunteer'),'unhcr')[0][0]['description'])
 def test_destination_rejected(self):
  for path in ['https://evil.test/job/1','/job/../private','/job/%2e%2e/private']:
   with self.assertRaises(ValueError):un_workday.parse_page(self.payload(path=path),'wfp')
 def test_duplicate_rejected(self):
  payload=self.payload();payload['jobPostings']*=2
  with self.assertRaises(ValueError):un_workday.parse_page(payload,'unhcr')
 def test_install_idempotence(self):
  with tempfile.TemporaryDirectory() as tmp:
   with zipfile.ZipFile('collector.zip') as z:z.extractall(tmp)
   with zipfile.ZipFile('repairs.zip') as z:z.extractall(tmp)
   install(tmp);p=Path(tmp)/'collector/public_feeds.py';first=p.read_text();install(tmp);self.assertEqual(first,p.read_text());feeds=json.loads((Path(tmp)/'collector/data/feeds.json').read_text());self.assertEqual(sum(f['board']=='unhcr' for f in feeds),1);compile(first,str(p),'exec')
if __name__=='__main__':unittest.main()
