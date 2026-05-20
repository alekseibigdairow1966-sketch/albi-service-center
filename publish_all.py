# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import os
import time
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

TOKEN = '8523648387:AAEhmf30rvtXjv-40lxscm3gItFboNwhnbA'
CHANNEL = '@albi_service_semey'
BASE = 'https://www.albi-service.kz'
HEADERS = {'User-Agent': 'Mozilla/5.0'}

ARTICLES = [
    'https://www.albi-service.kz/blog/sovety/sovet-pri-remonte-telefona/',
    'https://www.albi-service.kz/blog/sovety/telefon-upal-i-displej-razbilsya/',
    'https://www.albi-service.kz/blog/sovety/telefon-upal-v-vodu/',
    'https://www.albi-service.kz/blog/sovety/sovety-po-zaryadke-i-nastrojke-telefona/',
    'https://www.albi-service.kz/blog/pomoshh-telefony-samsung/nashi-rekomendaczii-po-uhodu-za-smartfonami/',
    'https://www.albi-service.kz/blog/pomoshh-telefony-samsung/rukovodstvo-po-osnovnym-funkcziyam-smartfona-samsung/',
    'https://www.albi-service.kz/blog/pomoshh-telefony-samsung/pochemu-smartfon-peregrevaetsya/',
    'https://www.albi-service.kz/blog/pomoshh-telefony-samsung/zashhita-telefona-ot-povrezhdenij/',
    'https://www.albi-service.kz/blog/sovety/kak-prodlit-srok-sluzhby-batarei/',
    'https://www.albi-service.kz/blog/stati/pochemu-stoit-doveryat-avtorizovannomu-servisnomu-czentru/',
    'https://www.albi-service.kz/blog/stati/remont-telefonov-samsung/',
    'https://www.albi-service.kz/blog/stati/pravila-provedenija-garantijnogo-i-post-garantijnogo-obsluzhivanija-v-avtorizovannom-servisnom-centre-albi-asc/',
    'https://www.albi-service.kz/blog/stati/samsung-care/',
    'https://www.albi-service.kz/blog/stati/samsung-sare-adh-zashhita-ekrana/',
    'https://www.albi-service.kz/blog/stati/faq/',
]

MAX_MSG = 4000
log_lines = []

def log(msg):
    print(msg)
    log_lines.append(msg)

def extract_article_text(soup):
    """Find the article content container and extract clean text from it."""
    content_div = soup.find('div', class_='articles-typical__content')
    if not content_div:
        content_div = soup.find('div', class_='entry-content')
    if not content_div:
        return ''

    # Remove unwanted elements
    for tag in content_div.find_all(['section']):
        tag.decompose()
    for tag in content_div.find_all('div'):
        cls = ' '.join(tag.get('class', []))
        if 'spacer' in cls or 'wp-block-spacer' in cls:
            tag.decompose()
    # Remove back-link
    back = content_div.find('div', class_='articles-typical__back-link')
    if back:
        back.decompose()

    # Collect meaningful text from relevant tags
    parts = []
    for tag in content_div.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'ul', 'ol', 'li', 'blockquote']):
        text = tag.get_text(strip=True)
        if len(text) > 3 and 'Похожие статьи' not in text and 'Вернуться назад' not in text:
            parts.append(text)

    return '\n\n'.join(parts)

def find_article_image(soup):
    """Find the actual article image."""
    # Method 1: first wp-block-image img inside articles-typical__content
    content_div = soup.find('div', class_='articles-typical__content')
    if content_div:
        img_div = content_div.find('div', class_='wp-block-image')
        if img_div:
            img = img_div.find('img')
            if img:
                src = img.get('src') or img.get('data-src')
                if src:
                    return src

    # Method 2: og:image meta tag
    og = soup.find('meta', attrs={'property': 'og:image'})
    if og:
        src = og.get('content', '')
        if src and '/wp-content/uploads/' in src:
            return src

    # Method 3: wp-post-image
    img = soup.find('img', class_='wp-post-image')
    if img:
        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
        if src and '/wp-content/uploads/' in src:
            return src

    # Method 4: any wp-content upload image
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src')
        if src and '/wp-content/uploads/' in src:
            if not any(skip in src.lower() for skip in ['icon', 'arrow', 'check', 'svg', 'logo', 'whats', 'telegram', 'instagram']):
                return src

    return None

def send_long_text(text, link_url):
    if link_url:
        text += '\n\nИсточник: ' + link_url

    chunks = []
    while len(text) > MAX_MSG:
        split_at = text.rfind('\n\n', 0, MAX_MSG)
        if split_at == -1:
            split_at = text.rfind('\n', 0, MAX_MSG)
        if split_at == -1 or split_at < MAX_MSG // 2:
            split_at = MAX_MSG
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    if text.strip():
        chunks.append(text.strip())

    for chunk in chunks:
        r = requests.post(f'https://api.telegram.org/bot{TOKEN}/sendMessage',
            json={'chat_id': CHANNEL, 'text': chunk[:MAX_MSG]},
            timeout=15)
        if not r.json().get('ok'):
            log(f'  ERROR: {r.json().get("description", "")}')
            return False
        time.sleep(1)
    return True

def send_article(title, text, img_url, article_url):
    if img_url:
        try:
            log(f'  Downloading image...')
            img_r = requests.get(img_url, headers=HEADERS, timeout=15, stream=True)
            img_r.raise_for_status()
            with open('_temp.jpg', 'wb') as f:
                for chunk in img_r.iter_content(8192):
                    f.write(chunk)
            fsize = os.path.getsize('_temp.jpg')
            log(f'  Image size: {fsize} bytes')

            intro = text[:600].strip()
            caption = f'{title}\n\n{intro}\n\n...'
            if fsize > 1000 and len(caption) <= 1024:
                with open('_temp.jpg', 'rb') as p:
                    resp = requests.post(f'https://api.telegram.org/bot{TOKEN}/sendPhoto',
                        data={'chat_id': CHANNEL, 'caption': caption},
                        files={'photo': p}, timeout=30)
                os.remove('_temp.jpg')
                if resp.json().get('ok'):
                    log(f'  Photo sent')
                    time.sleep(1.5)
                    ok = send_long_text(text, article_url)
                    if ok:
                        log(f'  Full text sent')
                        return True
                    return False
                else:
                    log(f'  Photo error: {resp.json().get("description", "")}')
            else:
                log(f'  Skipping photo (too small or caption too long)')
                if os.path.exists('_temp.jpg'):
                    os.remove('_temp.jpg')
        except Exception as e:
            log(f'  Photo error: {e}')
            if os.path.exists('_temp.jpg'):
                os.remove('_temp.jpg')

    full_text = f'{title}\n\n{text}'
    if send_long_text(full_text, article_url):
        log(f'  Full text sent (no photo)')
        return True
    return False

def get_article(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        # Get title
        h1 = soup.find('h1') or soup.find('h2')
        title = h1.get_text(strip=True) if h1 else 'No title'
        # Get article body only
        text = extract_article_text(soup)
        # Get image
        img_url = find_article_image(soup)
        if img_url and img_url.startswith('/'):
            img_url = BASE + img_url
        return title, text, img_url
    except Exception as e:
        return None, None, None, str(e)

log('=' * 50)
log('PUBLISHING FULL ARTICLES')
log('=' * 50)
log('')

try:
    r = requests.get(f'https://api.telegram.org/bot{TOKEN}/getMe', timeout=10)
    d = r.json()
    if d.get('ok'):
        log(f'Bot OK: @{d["result"]["username"]}')
    else:
        log(f'Bot ERROR: {d}')
        sys.exit(1)
except Exception as e:
    log(f'Bot ERROR: {e}')
    sys.exit(1)

log('')
log(f'Found {len(ARTICLES)} articles. Starting...')
log('')

success = 0
fail = 0

for i, url in enumerate(ARTICLES, 1):
    log(f'[{i}/{len(ARTICLES)}] {url}')
    try:
        result = get_article(url)
        if len(result) == 4:
            log(f'  ERROR: {result[3]}')
            fail += 1
            continue
        title, text, img = result

        if not text or len(text) < 50:
            log(f'  SKIPPED - too little text ({len(text)} chars)')
            fail += 1
            continue

        log(f'  Title: {title}')
        log(f'  Text: {len(text)} chars')
        log(f'  Image: {img if img else "NO"}')

        if send_article(title, text, img, url):
            success += 1
        else:
            fail += 1

    except Exception as e:
        log(f'  ERROR: {e}')
        fail += 1

    if i < len(ARTICLES):
        time.sleep(3)

log('')
log('=' * 50)
log(f'DONE! Success: {success}, Failed: {fail}')
log('=' * 50)

with open('publish_log.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(log_lines))
