import os
import re
import json
import requests
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.cia.gov"
SEARCH_URL = "https://www.cia.gov/readingroom/search/site/"
SETTINGS_DIR = "settings"
VISITED_LOG = os.path.join(SETTINGS_DIR, "visited_urls.json")
STATUS_LOG = os.path.join(SETTINGS_DIR, "download_status.jsonl")
PAGINATION_STATE = os.path.join(SETTINGS_DIR, "pagination_state.json")
DATA_DIR = "data"
PDF_DIR = os.path.join(DATA_DIR, "PDFs")
META_DIR = os.path.join(DATA_DIR, "metadata")

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)
os.makedirs(SETTINGS_DIR, exist_ok=True)

# Load visited
if os.path.exists(VISITED_LOG):
    with open(VISITED_LOG, "r") as f:
        visited = set(json.load(f))
else:
    visited = set()

def save_visited():
    with open(VISITED_LOG, "w") as f:
        json.dump(sorted(visited), f, indent=2)

def log_status(entry):
    with open(STATUS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def slugify(text):
    return re.sub(r'[^\w\-_. ]', '', text).strip().replace(" ", "_")

def save_metadata(doc_id, metadata_dict):
    path = os.path.join(META_DIR, f"{doc_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata_dict, f, indent=2, ensure_ascii=False)

def download_pdf(pdf_url, filename):
    if os.path.exists(filename):
        print(f"✅ Already downloaded: {filename}")
        return True
    try:
        r = requests.get(pdf_url, timeout=20)
        if r.status_code == 200:
            with open(filename, "wb") as f:
                f.write(r.content)
            print(f"⬇️ Downloaded {filename}")
            return True
        else:
            print(f"❌ PDF failed (status {r.status_code}): {pdf_url}")
    except Exception as e:
        print(f"❌ Error downloading PDF: {e}")
    return False

def load_last_page():
    if os.path.exists(PAGINATION_STATE):
        with open(PAGINATION_STATE, "r") as f:
            return json.load(f).get("last_page", 0)
    return 0

def save_last_page(page_num):
    with open(PAGINATION_STATE, "w") as f:
        json.dump({"last_page": page_num}, f)

def scrape_document(page, url):
    if url in visited:
        print(f"✅ Skipping (already visited): {url}")
        return
    print(f"📄 Visiting: {url}")

    try:
        page.goto(url, timeout=30000)
        page.wait_for_timeout(1500)

        title = page.title()

        pdf_links = page.evaluate("""() => {
            let links = Array.from(document.querySelectorAll('a'));
            return links
                .filter(l => l.href && l.href.endsWith('.pdf'))
                .map(l => l.href);
        }""")

        metadata = page.evaluate("""() => {
            const rows = Array.from(document.querySelectorAll("div.field"));
            const out = {};
            for (let row of rows) {
                const label = row.querySelector(".field-label");
                const value = row.querySelector(".field-item");
                if (label && value) {
                    out[label.innerText.trim().replace(':','')] = value.innerText.trim();
                }
            }
            return out;
        }""")

        downloaded = False
        downloaded_files = []

        rdp_match = re.search(r'(CIA-RDP\S+)', url)
        if not rdp_match and 'Document Number (FOIA) /ESDN (CREST)' in metadata:
            rdp_match = re.search(r'(CIA-RDP\S+)', metadata.get('Document Number (FOIA) /ESDN (CREST)', ''))
        doc_id = rdp_match.group(1) if rdp_match else slugify(title)[:40]

        if pdf_links:
            for idx, pdf_link in enumerate(pdf_links):
                suffix = f"_{idx+1}" if len(pdf_links) > 1 else ""
                filename = f"{slugify(title)}_{doc_id}{suffix}.pdf"
                path = os.path.join(PDF_DIR, filename)
                if download_pdf(pdf_link, path):
                    downloaded = True
                    downloaded_files.append(path)
        else:
            print("⚠️ No PDFs found on this page.")

        visited.add(url)
        save_visited()

        doc_record = {
            "url": url,
            "title": title,
            "pdf_urls": pdf_links,
            "downloaded": downloaded,
            "downloaded_files": downloaded_files,
            "metadata": metadata
        }

        save_metadata(doc_id, doc_record)
        log_status(doc_record)

    except Exception as e:
        print(f"❌ Failed to scrape document: {e}")

def scrape_index_pages(playwright, start_year=2012, max_pages=500):
    browser = playwright.chromium.launch(headless=False, slow_mo=50)
    page = browser.new_page()

    start_page = load_last_page()

    for page_num in range(start_page, start_page + max_pages):
        print(f"\n📑 Scraping index page {page_num + 1} for year {start_year}")
        search_url = (
            f"{SEARCH_URL}?page={page_num}"
            f"&f%5B0%5D=ds_created%3A%5B{start_year}-01-01T00%3A00%3A00Z"
            f"%20TO%20{start_year + 1}-01-01T00%3A00%3A00Z%5D"
        )
        try:
            page.goto(search_url, timeout=30000)
            page.wait_for_timeout(2000)

            anchors = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('#block-system-main > div > ol > li h3 a'))
                    .map(a => a.href)
                    .filter(href => href.includes('/readingroom/'));
            }""")

            if not anchors:
                print("🛑 No more links found on this page.")
                break

            for href in anchors:
                if href.startswith("https://www.cia.gov/readingroom/"):
                    scrape_document(page, href)

            save_last_page(page_num + 1)

        except Exception as e:
            print(f"❌ Failed to scrape index page {page_num}: {e}")
            break

    browser.close()

# ---- MAIN ----
if __name__ == "__main__":
    with sync_playwright() as p:
        scrape_index_pages(p, start_year=2012, max_pages=500)
