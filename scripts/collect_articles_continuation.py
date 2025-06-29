import os
import re
import json
import requests
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
import time

BASE_URL = "https://www.cia.gov"
SEARCH_URL = "https://www.cia.gov/readingroom/search/site"
SETTINGS_DIR = "settings"
VISITED_LOG = os.path.join(SETTINGS_DIR, "visited_urls.json")
STATUS_LOG = os.path.join(SETTINGS_DIR, "download_status.jsonl")
SCRAPE_PROGRESS = os.path.join(SETTINGS_DIR, "scrape_progress.json")
UNAVAILABLE_LOG = os.path.join(SETTINGS_DIR, "unavailables.json")
DATA_DIR = "data"
PDF_DIR = os.path.join(DATA_DIR, "PDFs")
META_DIR = os.path.join(DATA_DIR, "metadata")

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)
os.makedirs(SETTINGS_DIR, exist_ok=True)

if os.path.exists(VISITED_LOG):
    with open(VISITED_LOG, "r") as f:
        visited = set(json.load(f))
else:
    visited = set()

if os.path.exists(UNAVAILABLE_LOG):
    with open(UNAVAILABLE_LOG, "r") as f:
        unavailables = set(json.load(f))
else:
    unavailables = set()

def save_visited():
    with open(VISITED_LOG, "w") as f:
        json.dump(sorted(visited), f, indent=2)

def save_unavailables():
    with open(UNAVAILABLE_LOG, "w") as f:
        json.dump(sorted(unavailables), f, indent=2)

def log_status(entry):
    with open(STATUS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def slugify(text):
    return re.sub(r'[^\w\-_. ]', '', text).strip().replace(" ", "_")

def save_metadata(doc_id, metadata_dict):
    path = os.path.join(META_DIR, f"{doc_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata_dict, f, indent=2, ensure_ascii=False)

def save_progress(year, page):
    progress = {}
    if os.path.exists(SCRAPE_PROGRESS):
        with open(SCRAPE_PROGRESS, "r") as f:
            progress = json.load(f)
    progress[str(year)] = page
    with open(SCRAPE_PROGRESS, "w") as f:
        json.dump(progress, f, indent=2)

def get_progress(year):
    if os.path.exists(SCRAPE_PROGRESS):
        with open(SCRAPE_PROGRESS, "r") as f:
            progress = json.load(f)
        last = progress.get(str(year), 0)  # Start from 0 if no progress exists
        return last
    return 0  # Start from page 0 if no progress file exists

def show_progress():
    """Display current progress for all years"""
    if os.path.exists(SCRAPE_PROGRESS):
        with open(SCRAPE_PROGRESS, "r") as f:
            progress = json.load(f)
        print("📊 Current Progress:")
        for year in sorted(progress.keys()):
            print(f"  Year {year}: Page {progress[year]}")
    else:
        print("📊 No progress file found - will start from page 0")

def show_unavailables():
    """Display unavailable pages"""
    if unavailables:
        print(f"🚫 Unavailable pages ({len(unavailables)}):")
        for url in sorted(unavailables):
            print(f"  {url}")
    else:
        print("🚫 No unavailable pages recorded")

def download_pdf(pdf_url, filename):
    if os.path.exists(filename):
        print(f"✅ Already downloaded: {filename}")
        return True
    try:
        r = requests.get(pdf_url, timeout=60)
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

def check_page_unavailable(page):
    """Check if the current page is unavailable"""
    try:
        page_content = page.content()
        return "unavailable" in page_content.lower()
    except:
        return False

def scrape_document(page, url):
    if url in visited:
        print(f"✅ Skipping (already visited): {url}")
        return
    if url in unavailables:
        print(f"🚫 Skipping (known unavailable): {url}")
        return
    print(f"📄 Visiting: {url}")

    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(1500)

        title = page.title()
        
        # Check if page is unavailable
        if check_page_unavailable(page):
            print(f"🚫 Page unavailable: {url}")
            unavailables.add(url)
            save_unavailables()
            return

        pdf_links = page.evaluate("""() => {
            let links = Array.from(document.querySelectorAll('a'));
            return links
                .filter(l => l.href && (
                    l.href.toLowerCase().endsWith('.pdf') ||
                    l.href.toLowerCase().includes('/docs/') ||
                    l.innerText.toLowerCase().includes('pdf')
                ))
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

def scrape_from_url(playwright, start_url, start_year=2012):
    """Start scraping from a specific URL"""
    browser = playwright.chromium.launch(headless=False, slow_mo=50)
    page = browser.new_page()

    print(f"🚀 Starting from specific URL: {start_url}")
    
    # Extract page number from URL
    page_match = re.search(r'page=(\d+)', start_url)
    if page_match:
        page_num = int(page_match.group(1))
        print(f"📄 Detected page number: {page_num}")
    else:
        page_num = 0
        print(f"📄 No page number found, starting from 0")

    # Extract year from URL
    year_match = re.search(r'(\d{4})-01-01T00', start_url)
    if year_match:
        start_year = int(year_match.group(1))
        print(f"📅 Detected year: {start_year}")

    save_progress(start_year, page_num)
    
    # Flag to track if we've used the original URL
    used_original_url = False

    while True:
        print(f"\n📑 Scraping index page {page_num} for year {start_year}")
        save_progress(start_year, page_num)

        if not used_original_url:
            # Use the provided start URL for the first iteration
            search_url = start_url
            used_original_url = True
        else:
            # Construct URL for subsequent pages
            search_url = (
                f"{SEARCH_URL}?page={page_num}"
                f"&f%5B0%5D=ds_created%3A%5B{start_year}-01-01T00%3A00%3A00Z"
                f"%20TO%20{start_year + 1}-01-01T00%3A00%3A00Z%5D"
            )

        max_forced_reloads = 3
        for forced_reload in range(max_forced_reloads):
            try:
                page.goto(search_url, timeout=60000)
                page.wait_for_timeout(200)  # Let the page start loading
                # Rapidly poll the URL for up to 2 seconds
                intended_url_seen = False
                for _ in range(20):  # 20 x 100ms = 2 seconds
                    current_url = page.url
                    if "search/site" in current_url:
                        intended_url_seen = True
                        # If we see the main page, break out of polling
                        break
                    elif "/readingroom" == current_url.rstrip("/") or current_url.rstrip("/").endswith("/readingroom"):
                        # If redirected to main page, force reload intended URL
                        print(f"⚠️ Detected redirect to main page during polling (forced reload {forced_reload+1}/{max_forced_reloads}) - forcing intended URL again...")
                        page.goto(search_url, timeout=60000)
                        page.wait_for_timeout(200)
                        intended_url_seen = False
                        break
                    time.sleep(0.1)
                if intended_url_seen:
                    break  # Proceed if we saw the intended URL
            except Exception as e:
                print(f"❌ Exception during page load: {e}")
                if forced_reload == max_forced_reloads - 1:
                    print(f"❌ Failed to load intended page after {max_forced_reloads} forced reloads. Skipping.")
                    browser.close()
                    return
        else:
            print(f"🔄 Still redirected after {max_forced_reloads} forced reloads. Breaking.")
            print(f"📊 Reached end of results for year {start_year} at page {page_num}")
            break

        # Check if search page is unavailable
        if check_page_unavailable(page):
            print(f"🚫 Search page {page_num} for year {start_year} is unavailable, skipping to next page")
            page_num += 1
            save_progress(start_year, page_num)
            continue

        # Check if we're on a page with search results
        page_title = page.title()
        if "Freedom of Information Act Electronic Reading Room" in page_title and "search" not in page.url.lower():
            print(f"📊 Reached end of search results for year {start_year} at page {page_num}")
            print(f"🔄 Moving to next year ({start_year + 1})...")
            # Reset progress for next year and continue
            start_year += 1
            page_num = 0
            used_original_url = False  # Reset flag for new year
            save_progress(start_year, page_num)
            continue

        anchors = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('#block-system-main > div > ol > li h3 a'))
                .map(a => a.href)
                .filter(href => href.includes('/readingroom/'));
        }""")

        if not anchors:
            print("🛑 No more links found on this page.")
            # Check if this might be the end of results
            page_content = page.content()
            if "Freedom of Information Act Electronic Reading Room" in page_content:
                print(f"📊 Reached end of results for year {start_year} at page {page_num}")
                print(f"🔄 Moving to next year ({start_year + 1})...")
                # Reset progress for next year and continue
                start_year += 1
                page_num = 0
                used_original_url = False  # Reset flag for new year
                save_progress(start_year, page_num)
                continue
            break

        for href in anchors:
            if href.startswith("https://www.cia.gov/readingroom/"):
                scrape_document(page, href)

        page_num += 1

    browser.close()

def scrape_index_pages(playwright, start_year=2012):
    browser = playwright.chromium.launch(headless=False, slow_mo=50)
    page = browser.new_page()

    start_page = get_progress(start_year)
    print(f"🚀 Starting from page {start_page} for year {start_year}")

    page_num = start_page
    while True:
        print(f"\n📑 Scraping index page {page_num} for year {start_year}")
        save_progress(start_year, page_num)  # Save current page being processed

        search_url = (
            f"{SEARCH_URL}?page={page_num}"
            f"&f%5B0%5D=ds_created%3A%5B{start_year}-01-01T00%3A00%3A00Z"
            f"%20TO%20{start_year + 1}-01-01T00%3A00%3A00Z%5D"
        )

        try:
            page.goto(search_url, timeout=60000)
            page.wait_for_timeout(2000)

            # Check if search page is unavailable
            if check_page_unavailable(page):
                print(f"🚫 Search page {page_num} for year {start_year} is unavailable, skipping to next page")
                page_num += 1
                save_progress(start_year, page_num)
                continue

            # Check if we've been redirected to the main reading room page
            current_url = page.url
            if "search/site" not in current_url:
                print(f"🔄 Redirected to main page: {current_url}")
                print(f"📊 Reached end of results for year {start_year} at page {page_num}")
                break

            # Check if we're on a page with search results
            page_title = page.title()
            if "Freedom of Information Act Electronic Reading Room" in page_title and "search" not in current_url.lower():
                print(f"📊 Reached end of search results for year {start_year} at page {page_num}")
                print(f"🔄 Moving to next year ({start_year + 1})...")
                
                # Reset progress for next year and continue
                start_year += 1
                page_num = 0
                save_progress(start_year, page_num)
                continue

            anchors = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('#block-system-main > div > ol > li h3 a'))
                    .map(a => a.href)
                    .filter(href => href.includes('/readingroom/'));
            }""")

            if not anchors:
                print("🛑 No more links found on this page.")
                # Check if this might be the end of results
                page_content = page.content()
                if "Freedom of Information Act Electronic Reading Room" in page_content:
                    print(f"📊 Reached end of results for year {start_year} at page {page_num}")
                    print(f"🔄 Moving to next year ({start_year + 1})...")
                    
                    # Reset progress for next year and continue
                    start_year += 1
                    page_num = 0
                    save_progress(start_year, page_num)
                    continue
                break

            for href in anchors:
                if href.startswith("https://www.cia.gov/readingroom/"):
                    scrape_document(page, href)

        except Exception as e:
            print(f"❌ Failed to scrape index page {page_num}: {e}")
            break

        page_num += 1

    browser.close()

if __name__ == "__main__":
    import sys
    
    # Show current progress
    show_progress()
    show_unavailables()
    
    start_year = 2012
    start_url = None

    if len(sys.argv) > 1:
        # Check if first argument is a URL
        if sys.argv[1].startswith("http"):
            start_url = sys.argv[1]
            print(f"🎯 Starting scrape from URL: {start_url}")
        else:
            start_year = int(sys.argv[1])
            print(f"🎯 Starting scrape for year {start_year}")
    else:
        # Prompt user for URL if not provided
        user_input = input("Paste the CIA Reading Room search URL to start from (or press Enter to use year mode): ").strip()
        if user_input.startswith("http"):
            start_url = user_input
            print(f"🎯 Starting scrape from URL: {start_url}")
        else:
            print("No URL provided, using year mode.")

    with sync_playwright() as p:
        if start_url:
            scrape_from_url(p, start_url)
        else:
            scrape_index_pages(p, start_year=start_year)