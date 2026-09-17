#!/usr/bin/env python3
"""Generate books-covers.json by adding a cover placeholder URL to each book.
Uses placehold.co to create 200x300 placeholder images with the book title text.
"""
import json
import urllib.parse
from pathlib import Path

p = Path(__file__).parent
books_file = p / 'books.json'
if not books_file.exists():
    raise SystemExit('books.json not found in the project root')

books = json.loads(books_file.read_text())
new = []
for b in books:
    title = b.get('title', '')[:60]
    text = urllib.parse.quote_plus(title or 'Book')
    # placehold.co supports query params for BG/FG colors but using defaults is fine
    cover = f'https://placehold.co/200x300/png?text={text}&bg=efefef&fc=333333'
    nb = dict(b)
    nb['cover'] = cover
    new.append(nb)

out_file = p / 'books-covers.json'
out_file.write_text(json.dumps(new, indent=2, ensure_ascii=False))
print(f'Wrote {len(new)} books to {out_file}')
