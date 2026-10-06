import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import probe as p

class Tests(unittest.TestCase):
    def test_id_olx_not_category(self):
        self.assertEqual(p.listing_id('https://www.olx.pl/d/oferta/auto-CID5-ID1cndmU.html?x=y'),'ID1cndmU')
    def test_id_otomoto(self):
        self.assertEqual(p.listing_id('https://www.otomoto.pl/osobowe/oferta/auto-ID6IgSC6.html'),'ID6IgSC6')
    def test_wrong_domain(self):
        self.assertIsNone(p.canonical('https://www.olx.pl.evil.test/d/oferta/a-ID1Ab.html','olx',True))
        self.assertIsNone(p.canonical('http://www.olx.pl/d/oferta/a-ID1Ab.html','olx',True))
    def test_category_not_detail(self):
        self.assertIsNone(p.canonical('https://www.olx.pl/motoryzacja','olx',True))
    def test_tracking_removed(self):
        self.assertEqual(p.canonical('https://www.olx.pl/d/oferta/a-ID1Ab.html?search=xx#x','olx',True),'https://www.olx.pl/d/oferta/a-ID1Ab.html')
    def test_403_not_gone(self):
        self.assertEqual(p.classify(403,'',''),'http_403')
    def test_200_not_success(self):
        self.assertEqual(p.classify(200,'Home',''),'http_ok_content_not_yet_validated')
    def test_200_challenge(self):
        self.assertEqual(p.classify(200,'Just a moment',''),'challenge_page')
    def test_dns_error(self):
        self.assertEqual(p.classify(None,'','', 'net::ERR_NAME_NOT_RESOLVED'),'dns_error')
    def test_timeout_not_sale(self):
        self.assertEqual(p.classify(None,'','', 'Timeout 30000ms exceeded'),'timeout')
    def test_410_not_sale(self):
        self.assertEqual(p.classify(410,'Gone',''),'removal_signal_not_sale')
    def test_empty_metadata(self):
        self.assertFalse(p.metadata('<html><p>200 KM, 50000 zł</p></html>','https://www.olx.pl/d/oferta/a-ID1Ab.html')['structured_listing_found'])
    def test_scoped_metadata(self):
        u='https://www.otomoto.pl/osobowe/oferta/a-ID6Ab.html'
        obj=[{'@type':'Car','url':u,'name':'Opel Insignia','offers':{'price':50000},'mileageFromOdometer':{'value':123000},'image':'https://ireland.apollo.olxcdn.com/a.jpg'}, {'@type':'Car','url':'https://www.otomoto.pl/osobowe/oferta/a-ID6Other.html','name':'other','offers':{'price':1},'image':'https://img.test/other.jpg'}]
        got=p.metadata('<script type="application/ld+json">'+json.dumps(obj)+'</script>',u)
        self.assertTrue(got['structured_listing_found']); self.assertEqual(got['fields']['price'],50000)
        self.assertEqual(len(got['image_candidates']),1)
    def test_ambiguous_products(self):
        objs=[{'@type':'Product','name':'Opel Insignia','offers':{'price':1}},{'@type':'Product','name':'Other','offers':{'price':2}}]
        got=p.metadata('<script type="application/ld+json">'+json.dumps(objs)+'</script>','https://www.olx.pl/d/oferta/a-ID1Ab.html')
        self.assertFalse(got['structured_listing_found'])
    def test_page_next_and_urls(self):
        data=p.discover('<a href="/d/oferta/a-CID5-ID1Ab.html?search=x">auto</a><a rel="next" href="?page=2">next</a>','https://www.olx.pl/motoryzacja','olx')
        self.assertEqual(data['next'],'https://www.olx.pl/motoryzacja?page=2');self.assertEqual(len(data['links']),1)
    def test_image_private_and_redirect_not_allowed(self):
        self.assertFalse(p.image_allowed('https://127.0.0.1/private','olx'))
        self.assertFalse(p.image_allowed('https://olxcdn.com.evil.test/a','olx'))
        self.assertFalse(p.image_allowed('https://user@img.olxcdn.com/a','olx'))
        self.assertTrue(p.image_allowed('https://ireland.apollo.olxcdn.com/a','olx'))
    def test_output_atomic_json(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'report.json';p.write_json(path,{'a':1});p.write_json(path,{'a':2})
            self.assertEqual(json.loads(path.read_text()),{'a':2});self.assertFalse(list(Path(d).glob('*.tmp')))

if __name__=='__main__':unittest.main()
