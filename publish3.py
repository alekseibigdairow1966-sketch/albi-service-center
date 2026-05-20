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
MAX_MSG = 4000

ARTICLES = [
    ('https://www.albi-service.kz/blog/stati/pochemu-stoit-doveryat-avtorizovannomu-servisnomu-czentru/', 'О нас'),
    ('https://www.albi-service.kz/blog/stati/pravila-provedenija-garantijnogo-i-post-garantijnogo-obsluzhivanija-v-avtorizovannom-servisnom-centre-albi-asc/', 'Гарантийное обслуживание'),
    ('https://www.albi-service.kz/blog/stati/kak-otkryt-shampanskoe-bez-ruk-ne-prik/', 'Гарантийный ремонт'),
]

def get_article(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, 'html.parser')

    # Title from h1
    h1 = soup.find('h1')
    title = h1.get_text(strip=True) if h1 else 'No title'

    # Find the article content container
    content_div = soup.find('div', class_='articles-typical__content')
    if not content_div:
        # fallback: try entry-content
        content_div = soup.find('div', class_='entry-content')
    if not content_div:
        return title, '', None

    # Remove unwanted sections from content
    for tag in content_div.find_all(['section']):
        tag.decompose()

    # Remove spacer divs and empty p tags
    for tag in content_div.find_all('div'):
        cls = ' '.join(tag.get('class', []))
        if 'spacer' in cls or 'wp-block-spacer' in cls:
            tag.decompose()

    # Collect meaningful text
    parts = []
    for tag in content_div.find_all(['h2', 'h3', 'h4', 'h5', 'p', 'ul', 'ol', 'li', 'blockquote']):
        text = tag.get_text(strip=True)
        if len(text) > 3 and 'Похожие статьи' not in text and 'Вернуться назад' not in text:
            parts.append(text)

    body = '\n\n'.join(parts)

    # Find article image - first wp-block-image img
    img_url = None
    img_div = content_div.find('div', class_='wp-block-image')
    if img_div:
        img = img_div.find('img')
        if img:
            img_url = img.get('src') or img.get('data-src')

    # Fallback: og:image
    if not img_url:
        og = soup.find('meta', attrs={'property': 'og:image'})
        if og:
            img_url = og.get('content', '')

    return title, body, img_url

def send_long_text(text, link_url=None):
    if link_url:
        text += f'\n\nЧитать полностью: {link_url}'
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
            json={'chat_id': CHANNEL, 'text': chunk[:MAX_MSG]}, timeout=15)
        if not r.json().get('ok'):
            print(f'  TEXT ERROR: {r.json().get("description","")}')
            return False
        time.sleep(1.5)
    return True

print('=' * 40)
print('Publishing 3 articles')
print('=' * 40)

for i, (url, label) in enumerate(ARTICLES, 1):
    print(f'\n[{i}/3] {label}')
    try:
        title, body, img = get_article(url)
        print(f'  Title: {title}')
        print(f'  Body: {len(body)} chars')
        print(f'  Image: {img if img else "NO"}')

        if not body or len(body) < 50:
            print(f'  SKIPPED - too short')
            continue

        # Send photo with intro
        if img:
            try:
                print(f'  Downloading image...')
                img_r = requests.get(img, headers=HEADERS, timeout=15, stream=True)
                img_r.raise_for_status()
                with open('_temp.jpg', 'wb') as f:
                    for chunk in img_r.iter_content(8192):
                        f.write(chunk)
                fsize = os.path.getsize('_temp.jpg')
                print(f'  Image size: {fsize} bytes')

                intro = body[:600].strip()
                caption = f'{title}\n\n{intro}\n\n...'
                if fsize > 1000 and len(caption) <= 1024:
                    with open('_temp.jpg', 'rb') as p:
                        resp = requests.post(f'https://api.telegram.org/bot{TOKEN}/sendPhoto',
                            data={'chat_id': CHANNEL, 'caption': caption},
                            files={'photo': p}, timeout=30)
                    os.remove('_temp.jpg')
                    if resp.json().get('ok'):
                        print(f'  Photo sent OK')
                        time.sleep(2)
                        if send_long_text(body, url):
                            print(f'  Full text sent OK')
                        else:
                            print(f'  Full text FAILED')
                    else:
                        print(f'  Photo FAIL: {resp.json().get("description","")}')
                else:
                    print(f'  Skipping photo (too small/caption too long)')
                    if os.path.exists('_temp.jpg'):
                        os.remove('_temp.jpg')
            except Exception as e:
                print(f'  Photo error: {e}')
                if os.path.exists('_temp.jpg'):
                    os.remove('_temp.jpg')
        else:
            if send_long_text(title + '\n\n' + body, url):
                print(f'  Text sent OK')

    except Exception as e:
        print(f'  ERROR: {e}')

    if i < len(ARTICLES):
        time.sleep(3)

print('\nDONE!')
