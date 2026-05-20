# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import os

URL = 'https://www.albi-service.kz/blog/stati/pochemu-stoit-doveryat-avtorizovannomu-servisnomu-czentru/'
r = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.text, 'html.parser')

h1 = soup.find('h1')
if h1:
    print(f'H1: {h1.get_text(strip=True)}')
    print(f'H1 parent: {h1.parent.name}, class={h1.parent.get("class")}')
    print()
    # Show siblings
    sib = h1.find_next_sibling()
    for i in range(20):
        if not sib:
            print(f'Sibling {i}: None')
            break
        tag_name = sib.name
        cls = sib.get('class', [])
        txt = sib.get_text(strip=True)[:80]
        print(f'Sibling {i}: <{tag_name}> class={cls} text="{txt}"')
        sib = sib.find_next_sibling()
else:
    print('No h1 found')
    h2 = soup.find('h2')
    if h2:
        print(f'H2: {h2.get_text(strip=True)}')
        sib = h2.find_next_sibling()
        for i in range(20):
            if not sib:
                print(f'Sibling {i}: None')
                break
            tag_name = sib.name
            cls = sib.get('class', [])
            txt = sib.get_text(strip=True)[:80]
            print(f'Sibling {i}: <{tag_name}> class={cls} text="{txt}"')
            sib = sib.find_next_sibling()

# Also check for article tags or common WP classes
for tag in soup.find_all(['article', 'div']):
    cls = tag.get('class', [])
    if any(c in ' '.join(cls) for c in ['entry-content', 'post-content', 'single-post', 'article', 'content']):
        txt = tag.get_text(strip=True)[:200]
        print(f'\nFound container: <{tag.name}> class={cls}')
        print(f'First 200 chars: {txt}')
        break
