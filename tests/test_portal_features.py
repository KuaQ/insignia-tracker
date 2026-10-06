import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from scripts.prepare_portal import BASE, distance, identity, identities, source_info, clean_text, enrich, valid_url

class PortalTests(unittest.TestCase):
    def test_olx_real_id_not_category(self):
        u='https://www.olx.pl/d/oferta/insignia-CID5-ID1cndmU.html?search_reason=promoted'
        self.assertEqual(identity('olx',u),'ID1cndmU')
        self.assertIn('1098981800',identities('olx',u))
        self.assertIn('1099130583',identities('olx','https://www.olx.pl/d/oferta/insignia-CID5-ID1cnQ4D.html'))
    def test_bad_urls(self):
        self.assertIsNone(valid_url('https://evil.test/olx.pl/test','olx'))
        self.assertIsNone(valid_url('javascript:alert(1)'))
    def test_distance(self):
        self.assertAlmostEqual(distance(BASE,BASE),0)
        self.assertGreater(distance(BASE,{'lat':53.13333,'lon':23.16433}),250)
        self.assertLess(distance(BASE,{'lat':53.13333,'lon':23.16433}),300)
    def test_only_primary_product(self):
        source='<meta property="og:image" content="https://img.test/main.jpg"><script type="application/ld+json">'+json.dumps([{'@type':'Car','url':'https://www.otomoto.pl/osobowe/oferta/auto-ID6Good.html','image':['https://img.test/a.jpg']},{'@type':'Car','url':'https://www.otomoto.pl/osobowe/oferta/auto-ID6Other.html','image':['https://img.test/other.jpg']}])+'</script>'
        data=source_info(source,'otomoto','https://www.otomoto.pl/osobowe/oferta/auto-ID6Good.html')
        self.assertIn('https://img.test/a.jpg',data['images']);self.assertNotIn('https://img.test/other.jpg',data['images'])
    def test_gallery_excludes_recommendations(self):
        source='<div class="gallery"><img src="https://img.test/a.jpg"></div><div class="recommendations"><div class="gallery"><img src="https://img.test/b.jpg"></div></div>'
        data=source_info(source,'otomoto','https://www.otomoto.pl/osobowe/oferta/auto-ID6Good.html')
        self.assertIn('https://img.test/a.jpg',data['images']);self.assertNotIn('https://img.test/b.jpg',data['images'])
    def test_exact_next_ad_id(self):
        d={'props':{'pageProps':{'advert':{'id':'ID6Good','location':{'lat':53.1,'lon':18.2,'city':{'name':'Miasto'}},'photos':[{'url':'https://img.test/a.jpg'}]},'related':{'id':'ID6Other','location':{'lat':50,'lon':20}}}}}
        data=source_info('<script type="application/json">'+json.dumps(d)+'</script>','otomoto','https://www.otomoto.pl/osobowe/oferta/auto-ID6Good.html')
        self.assertEqual(data['location']['city'],'Miasto');self.assertEqual(data['location']['lat'],53.1)
    def test_strip_scripts_and_contact(self):
        s=clean_text('<p>Dobry <b>samochód</b></p><script>alert(1)</script>tel. 600-123-456 name@example.com')
        self.assertNotIn('alert',s);self.assertNotIn('600-123',s);self.assertNotIn('@',s)
    def test_enrich_preserves_rows_and_ignores_logo(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'dashboard').mkdir(); folder=root/'archive/test/20261006T132000Z';(folder/'media').mkdir(parents=True)
            row={'key':'ID6Good','status':'active','price_pln':50000,'history':[{'at':'2026-10-02','type':'first_seen'}], 'copies':[{'portal':'otomoto','portal_id':'ID6Good','url':None}]}
            payload={'meta':{},'listings':[row],'events':[]};(root/'dashboard/data.json').write_text(json.dumps(payload))
            url='https://www.otomoto.pl/osobowe/oferta/auto-ID6Good.html'
            saved={'portal':'otomoto','portal_id':'ID6Good','url':url,'image_urls':['https://img.test/car.jpg','https://img.test/logo.svg','https://img.test/other.jpg'],'price_pln':999999}
            (folder/'listing.json').write_text(json.dumps(saved))
            (folder/'manifest.json').write_text(json.dumps({'image_files':['media/01.jpg','media/02.jpg','media/03.jpg']}))
            Image.new('RGB',(800,600)).save(folder/'media/01.jpg');(folder/'media/02.jpg').write_text('<svg></svg>');Image.new('RGB',(900,600)).save(folder/'media/03.jpg')
            (folder/'source.html').write_text('<meta property="og:image" content="https://img.test/car.jpg">')
            result=enrich(root);r=result['listings'][0]
            self.assertEqual(r['price_pln'],50000);self.assertEqual(r['history'],row['history']);self.assertEqual(r['copies'][0]['url'],url)
            self.assertEqual(len(r['saved_previews'][0]['photos']),1)
            self.assertEqual(r['saved_previews'][0]['completeness'],'partial')
            self.assertIsNone(r['distance_km'])
            self.assertEqual(len(list((root/'dashboard/assets/photos').glob('*.webp'))),2)
            self.assertFalse(list((root/'dashboard').rglob('source.html')))

if __name__=='__main__':unittest.main()
