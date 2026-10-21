import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'collector'))
import updater

class FreelanceTests(unittest.TestCase):
    def row(self,title,id=1,location='Remote in EMEA',internal=12):
        return dict(id=id,internal_job_id=internal,title=title,location={'name':location},
            absolute_url=f'https://job-boards.greenhouse.io/testlio/jobs/{id}',content='')
    def normalize(self,*rows):
        return updater.normalized({'jobs':list(rows),'meta':{'total':len(rows)}},'testlio')[0]
    def test_onsite_title_beats_remote_bucket(self):
        self.assertEqual(self.normalize(self.row('Freelance Software Tester (On-Site in Vienna)'))[0]['work_mode'],'onsite')
        self.assertEqual(self.normalize(self.row('Freelancer - Get Paid to Visit St. Louis Airport'))[0]['work_mode'],'onsite')
    def test_future_pool_and_prospect_excluded(self):
        self.assertEqual(self.normalize(self.row('QA Tester (Future Roles)'),self.row('Talent Pool',2),self.row('Tester',3,internal=None)),[])
    def test_real_freelance_preserves_application(self):
        row=self.normalize(self.row('Freelance Tester',location='Remote in Austria'))[0]
        self.assertEqual(row['work_mode'],'remote')
        self.assertEqual(row['url'],'https://job-boards.greenhouse.io/testlio/jobs/1')
        self.assertIsNone(row['deadline'])

if __name__=='__main__':unittest.main()
