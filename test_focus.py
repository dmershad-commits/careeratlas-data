import unittest
from datetime import datetime,timezone
from focus_refresh import brac_rows,canonical_rows,pick,check_scholarships,signature
NOW=datetime(2026,10,24,7,tzinfo=timezone.utc)
class FocusTests(unittest.TestCase):
 def test_closed_expired_internal_and_nationality(self):
  r=dict(id=1,status='Live',is_external_job=True,application_deadline='2026-10-27 00:00:00',slug='test-1',job_title='Officer',job_location_details='Dhaka',intro_message1='Bangladeshi nationals only')
  self.assertEqual(len(brac_rows({'results':[r]},NOW)),1)
  for patch in [dict(status='Closed'),dict(is_external_job=False),dict(application_deadline='2026-10-24 00:00:00'),dict(intro_message1='All applicants'),dict(application_deadline='invalid')]:self.assertEqual(brac_rows({'results':[dict(r,**patch)]},NOW),[])
 def test_remote_geography(self):
  r=dict(id=2,title='Engineer',absolute_url='https://canonical.com/careers/2',location={'name':'Home based - Worldwide'})
  self.assertEqual(len(canonical_rows({'jobs':[r]},NOW)),1)
  r['location']['name']='Home based - EMEA';self.assertEqual(canonical_rows({'jobs':[r]},NOW),[])
 def test_replacement_and_removal(self):
  rows=[dict(id='new',deadline=None),dict(id='expired',deadline='2026-01-01T00:00:00Z')]
  self.assertEqual([r['id'] for r in pick(rows,[dict(id='removed')],2,NOW)],['new'])
 def test_changed_scholarships_fail_closed(self):
  r=dict(id='s',provider='University',source_url='https://example.org',evidence_sha256=signature('<p>Official terms</p>'))
  self.assertEqual(len(check_scholarships([r],NOW,lambda _: '<p>Official terms</p>')[0]),1)
  self.assertEqual(check_scholarships([r],NOW,lambda _: '<p>Changed terms</p>')[0],[])
  self.assertEqual(check_scholarships([dict(r,deadline_date='2026-10-24')],NOW,lambda _: '<p>Official terms</p>')[0],[])
if __name__=='__main__':unittest.main()
