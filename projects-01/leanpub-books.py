import json
import csv
import re
import os

def parse_books(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Normalize newlines
    content = content.replace('\r\n', '\n')
    # Split by empty lines (double newlines)
    blocks = re.split(r'\n\s*\n', content)

    books = []

    for block in blocks:
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if not lines:
            continue

        title = lines[0]
        book_data = {
            "title": title,
            "pdf": None,
            "epub": None,
            "other_links": []
        }

        for line in lines[1:]:
            # Extract URL - look for http:// or https://
            url_match = re.search(r'(https?://[^\s]+)', line)
            if url_match:
                url = url_match.group(1)
                lower_line = line.lower()
                if "pdf" in lower_line:
                    book_data["pdf"] = url
                elif "epub" in lower_line:
                    book_data["epub"] = url
                else:
                    book_data["other_links"].append(url)
        
        books.append(book_data)

    return books

def save_json(books, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(books, f, indent=4, ensure_ascii=False)

def save_csv(books, output_file):
    headers = ['Title', 'PDF', 'EPUB', 'Other Links']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for book in books:
            other = "; ".join(book["other_links"])
            writer.writerow([
                book["title"],
                book.get("pdf", "") or "",
                book.get("epub", "") or "",
                other
            ])

if __name__ == "__main__":
    input_file = "books_data.txt"
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Please save your book list to this file.")
    else:
        books = parse_books(input_file)
        save_json(books, "books.json")
        save_csv(books, "books.csv")
        print(f"Successfully processed {len(books)} books.")