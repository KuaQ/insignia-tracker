"""Enrich the built panel from local saved files only. Never refresh market observations.
Publishes safe gallery images (not arbitrary source HTML), known URLs and sourced locations.
"""
import hashlib
import html
import json
import math
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
BASE = {'city': 'Włocławek', 'lat': 52.66530, 'lon': 19.06080,
        'source': 'https://www.geonames.org/7532956/wloclawek.html'}
CITIES = {
 'Katowice': (50.21414, 19.00798, 'https://www.geonames.org/7530792/katowice.html'),
 'Wrocław': (51.10773, 17.03533, 'https://www.geonames.org/7531292/wroclaw.html'),
 'Białystok': (53.13333, 23.16433, 'https://www.geonames.org/776069/bialystok.html'),
}
# These are cities explicitly recorded in the historical reports, not inferred from VINs.
HISTORICAL_CITIES = {'ID6Ig2tj': 'Katowice', 'ID6IgtPG': 'Wrocław', 'AP3954-9545-RB': 'Białystok'}


def identity(portal, url):
    path = urlsplit(url or '').path
    pattern = r'(\d{4}-\d{4}-[A-Z]{2})/?$' if portal == 'autoplac' else r'-(ID[0-9A-Za-z]+)\.html$'
    m = re.search(pattern, path)
    return m.group(1) if m else None


def identities(portal, url):
    token = identity(portal, url)
    result = [token] if token else []
    if token and portal in ('olx', 'otomoto'):
        n = 0
        for c in token[2:]:
            n = n * 62 + '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'.index(c)
        result.append(str(n))
    return result


def valid_url(url, portal=None):
    try:
        u = urlsplit(url or '')
        hosts = {'otomoto': 'otomoto.pl', 'olx': 'olx.pl', 'autoplac': 'autoplac.pl'}
        host = hosts.get(portal)
        if u.scheme != 'https' or u.username or u.password:
            return None
        if host and u.hostname not in (host, 'www.' + host):
            return None
        return urlunsplit((u.scheme, u.netloc, u.path, '', ''))
    except ValueError:
        return None


def image_key(url):
    # Resized versions of an OLX/OTOMOTO photo have the same /files/ identifier.
    return (valid_url(url) or '').split('/image;')[0]


def distance(a, b):
    a1, a2, b1, b2 = map(math.radians, (a['lat'], a['lon'], b['lat'], b['lon']))
    h = math.sin((b1-a1)/2)**2 + math.cos(a1)*math.cos(b1)*math.sin((b2-a2)/2)**2
    return 6371.0088 * 2 * math.atan2(math.sqrt(h), math.sqrt(max(0, 1-h)))


class Source(HTMLParser):
    """Select source metadata/JSON-LD and gallery containers, excluding related offers."""
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.meta = {}; self.ld = []; self.page_data = []; self.gallery = []; self.stack = []; self.script = None; self.buf = []
        self.feed(source)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs); marker = ' '.join(str(a.get(k, '')) for k in ('class','id','data-testid','aria-label')).lower()
        excluded = any(w in marker for w in ('recommend','similar','related','suggest')) or (self.stack and self.stack[-1][2])
        gallery = ('gallery' in marker or 'galeria' in marker) or (self.stack and self.stack[-1][1])
        if tag == 'meta':
            self.meta[a.get('property') or a.get('name')] = a.get('content','')
        if tag == 'img' and gallery and not excluded:
            self.gallery.extend(a.get(k,'') for k in ('src','data-src','data-lazy-src'))
        if tag == 'script':
            self.script = 'ld' if a.get('type') == 'application/ld+json' else 'page' if a.get('type') == 'application/json' else None; self.buf = []
        if tag not in ('img','meta','link','br','hr','input','source','wbr','area','base','embed','param','track','col'):
            self.stack.append((tag, bool(gallery), bool(excluded)))
    def handle_endtag(self, tag):
        if tag == 'script':
            if self.script:
                try: (self.ld if self.script == 'ld' else self.page_data).append(json.loads(''.join(self.buf)))
                except (ValueError, TypeError): pass
            self.script = None; self.buf = []
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0] == tag:
                self.stack = self.stack[:i]; break
    def handle_data(self, data):
        if self.script: self.buf.append(data)


def objects(values):
    for value in values:
        if isinstance(value,list): yield from objects(value)
        elif isinstance(value,dict):
            yield value
            if '@graph' in value: yield from objects([value['@graph']])
            if isinstance(value.get('mainEntity'),dict): yield value['mainEntity']


def urls(value):
    if isinstance(value,str): return [value]
    if isinstance(value,list): return [u for x in value for u in urls(x)]
    if isinstance(value,dict): return urls(value.get('url') or value.get('contentUrl'))
    return []


def source_info(raw, portal, url):
    src = Source(raw)
    primary = []
    for obj in objects(src.ld):
        typ = obj.get('@type',[]); typ = [typ] if isinstance(typ,str) else typ
        if not set(typ).intersection({'Car','Vehicle','Product'}): continue
        obj_url = obj.get('url') or obj.get('@id')
        if obj_url and identity(portal,obj_url) and identity(portal,obj_url) != identity(portal,url): continue
        primary.append(obj)
    # Only JSON page-data objects with this precise ad ID, never related items.
    tokens = set(identities(portal,url))
    pending = list(src.page_data)
    while pending:
        value = pending.pop()
        if isinstance(value,list): pending.extend(value)
        elif isinstance(value,dict):
            if str(value.get('id')) in tokens and any(k in value for k in ('photos','images','parameters','location')):
                primary.append(value)
            pending.extend(v for v in value.values() if isinstance(v,(dict,list)))
    images = urls(src.meta.get('og:image')) + src.gallery
    location = None
    description = None
    for obj in primary:
        images.extend(urls(obj.get('image')))
        images.extend(urls(obj.get('photos')))
        images.extend(urls(obj.get('images')))
        if isinstance(obj.get('description'),str): description = obj['description']
        offers = obj.get('offers',{}); offers = offers[0] if isinstance(offers,list) and offers else offers
        seller = obj.get('seller') or (offers.get('seller') if isinstance(offers,dict) else {}) or {}
        for owner in (obj, seller, obj.get('location',{}), obj.get('map',{})):
            if not isinstance(owner,dict): continue
            geo = owner.get('geo') or owner.get('location') or owner; address = owner.get('address',{})
            if isinstance(geo,dict) and isinstance(geo.get('geo'),dict): geo = geo['geo']
            try:
                lat, lon = float(geo.get('latitude',geo.get('lat'))), float(geo.get('longitude',geo.get('lon',geo.get('lng'))))
                if 48 <= lat <= 55.5 and 14 <= lon <= 25:
                    city=address.get('addressLocality') if isinstance(address,dict) else None
                    city=city or owner.get('city') or (obj.get('location') or {}).get('city')
                    if isinstance(city,dict): city=city.get('name')
                    location = {'lat':lat,'lon':lon,'city':city if isinstance(city,str) else None}
            except (TypeError,ValueError,AttributeError): pass
    return {'images':{image_key(u) for u in images if valid_url(u)},'location':location,'description':description}


def clean_text(text):
    # Archive reader never executes downloaded HTML and omits unnecessary contact data.
    class Text(HTMLParser):
        def __init__(self): super().__init__(); self.parts=[]; self.hidden=0
        def handle_starttag(self,tag,attrs):
            if tag in ('script','style'): self.hidden+=1
        def handle_endtag(self,tag):
            if tag in ('script','style'): self.hidden=max(0,self.hidden-1)
            if tag in ('p','br','div','li'): self.parts.append('\n')
        def handle_data(self,data):
            if not self.hidden: self.parts.append(data)
    p=Text(); p.feed(text or '')
    text=' '.join(p.parts)
    text=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[kontakt pominięty]', text)
    text=re.sub(r'(?<!\w)(?:\+48\s*)?(?:\d[ -]?){9}(?!\w)', '[numer pominięty]', text)
    return text.strip()[:30000]


def publish_photos(folder, saved, manifest, trusted, out):
    published=[]; seen=set()
    for rel in manifest.get('image_files',[]):
        m=re.fullmatch(r'media/(\d+)\.[a-zA-Z0-9]+',rel)
        if not m: continue
        index=int(m.group(1))-1
        if not 0<=index<len(saved.get('image_urls',[])): continue
        key=image_key(saved['image_urls'][index])
        if not key or key not in trusted or key in seen: continue
        path=folder/rel
        if not path.is_file() or path.is_symlink(): continue
        try:
            with Image.open(path) as im:
                if im.format not in ('JPEG','PNG','WEBP') or im.width<320 or im.height<180: continue
                im=ImageOps.exif_transpose(im).convert('RGB'); im.thumbnail((1440,1080))
                digest=hashlib.sha256(path.read_bytes()).hexdigest()[:24]
                dest=out/'assets/photos'; dest.mkdir(parents=True,exist_ok=True)
                full=dest/(digest+'.webp'); thumb=dest/(digest+'-thumb.webp')
                if not full.exists(): im.save(full,'WEBP',quality=80,method=4)
                im.thumbnail((360,270))
                if not thumb.exists(): im.save(thumb,'WEBP',quality=77)
                published.append({'url':'./assets/photos/'+full.name,'thumbnail':'./assets/photos/'+thumb.name,'source_path':path.as_posix().split('/archive/')[-1]})
                seen.add(key)
        except (OSError,ValueError,Image.DecompressionBombError): continue
    return published


def enrich(root=ROOT):
    root=Path(root); out=root/'dashboard'
    payload=json.loads((out/'data.json').read_text(encoding='utf-8'))
    lookup={}
    for row in payload['listings']:
        row['saved_previews']=[]
        for cp in row.get('copies',[]):
            lookup[(cp['portal'],cp['portal_id'])]=row
            for token in identities(cp['portal'],cp.get('url')): lookup[(cp['portal'],token)]=row
    linked=0; photos=0; locations={}
    for path in sorted((root/'archive').glob('*/*/listing.json')):
        try:
            saved=json.loads(path.read_text(encoding='utf-8')); portal=saved.get('portal'); url=valid_url(saved.get('url'),portal)
            row=next((lookup[(portal,t)] for t in identities(portal,url) if (portal,t) in lookup),None)
            if not row or not url: continue
            tokens=identities(portal,url)
            for cp in row.get('copies',[]):
                if cp['portal']==portal and cp['portal_id'] in tokens and not cp.get('url'):
                    cp.update(url=url,url_source='saved_archive')
            raw=(path.parent/'source.html').read_text(encoding='utf-8',errors='replace')
            info=source_info(raw,portal,url)
            manifest=json.loads((path.parent/'manifest.json').read_text(encoding='utf-8'))
            gallery=publish_photos(path.parent,saved,manifest,info['images'],out)
            stamp=path.parent.name
            repo_url='https://github.com/KuaQ/insignia-tracker/tree/main/'+quote(path.parent.relative_to(root).as_posix(),safe='/')
            record={'at':stamp,'portal':portal,'source_url':url,'files_url':repo_url,'photos':gallery,'completeness':'partial','description':clean_text(info['description']) if info['description'] else None,
                    'note':'Archiwum testowe. Pokazujemy wyłącznie zapisane zdjęcia rozpoznane jako galeria tej oferty. To nie jest nowy odczyt ani pełna gwarantowana kopia.'}
            row['saved_previews'].append(record); linked+=1; photos+=len(gallery)
            if info['location']:
                locations.setdefault(row['key'],[]).append({**info['location'],'source':repo_url,'observed_at':manifest.get('archived_at') or stamp,'precision':'Punkt z metadanych archiwalnej strony, nie aktualny adres auta'})
        except (OSError,ValueError,KeyError,TypeError): continue
    # Also restore known complete URLs from the maintained explicit URL registry.
    tracked=root/'config/tracked_urls.json'
    if tracked.exists():
        for portal,links in json.loads(tracked.read_text(encoding='utf-8')).items():
            for link in links:
                tokens=identities(portal,link)
                for token in tokens:
                    row=lookup.get((portal,token))
                    if row:
                        for cp in row.get('copies',[]):
                            if cp['portal']==portal and cp['portal_id'] in tokens and not cp.get('url'): cp.update(url=valid_url(link,portal),url_source='tracked_urls')
    for row in payload['listings']:
        candidates=locations.get(row['key'],[])
        loc=row.get('location') if isinstance(row.get('location'),dict) else None
        if not loc and candidates:
            if all(distance(candidates[0],c)<30 for c in candidates[1:]): loc=candidates[-1]
            else: row['location_note']='Rozbieżne lokalizacje kopii; sprawdź u sprzedawcy.'
        if not loc and not candidates and row['key'] in HISTORICAL_CITIES:
            city=HISTORICAL_CITIES[row['key']]; lat,lon,source=CITIES[city]
            loc={'city':city,'lat':lat,'lon':lon,'source':source,'observed_at':'2026-10-06','precision':'Punkt referencyjny miasta; miejscowość z zapisanych raportów'}
        if loc:
            try:
                lat,lon=float(loc['lat']),float(loc['lon'])
                if not (48<=lat<=55.5 and 14<=lon<=25): raise ValueError('Not a Polish listing location')
                loc={**loc,'lat':lat,'lon':lon}
                row['location']=loc; row['distance_km']=round(distance(BASE,loc),1)
            except (KeyError,ValueError,TypeError): row['distance_km']=None
        else: row['distance_km']=None
    counts={'snapshots':linked,'photo_files_in_galleries':photos,'vehicles_with_photos':sum(any(a['photos'] for a in r['saved_previews']) for r in payload['listings']),
            'vehicles_with_distance':sum(r['distance_km'] is not None for r in payload['listings']),
            'copies_with_links':sum(bool(c.get('url')) for r in payload['listings'] for c in r.get('copies',[]))}
    payload['meta']['portal_features']={**counts,'distance_origin':BASE,'distance_method':'haversine_straight_line_not_road','version':1}
    text=json.dumps(payload,ensure_ascii=False,indent=2)
    (out/'data.json').write_text(text+'\n',encoding='utf-8')
    (out/'data.js').write_text('window.INSIGNIA_DATA = '+text+';\n',encoding='utf-8')
    print('Portal features:',json.dumps(counts,ensure_ascii=False))
    return payload

if __name__=='__main__': enrich()
