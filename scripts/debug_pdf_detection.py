#!/usr/bin/env python3
"""
Debug script to see what links are actually on CIA document pages
"""

from playwright.sync_api import sync_playwright
import re

def debug_page(url):
    """Debug a specific CIA document page to see what links are there"""
    print(f"🔍 Debugging page: {url}")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        page = browser.new_page()
        
        try:
            page.goto(url, timeout=60000)
            page.wait_for_timeout(2000)
            
            # Get page title
            title = page.title()
            print(f"📄 Page title: {title}")
            
            # Get all links on the page
            all_links = page.evaluate("""() => {
                let links = Array.from(document.querySelectorAll('a'));
                return links.map(l => ({
                    href: l.href,
                    text: l.innerText.trim(),
                    className: l.className,
                    id: l.id
                }));
            }""")
            
            print(f"\n📊 Found {len(all_links)} total links")
            
            # Show all links
            print("\n🔗 All links on page:")
            for i, link in enumerate(all_links[:20]):  # Show first 20
                print(f"  {i+1}. {link['text'][:50]} -> {link['href']}")
                if link['className']:
                    print(f"     Class: {link['className']}")
                if link['id']:
                    print(f"     ID: {link['id']}")
            
            if len(all_links) > 20:
                print(f"     ... and {len(all_links) - 20} more links")
            
            # Check for PDF links with current logic
            pdf_links_current = page.evaluate("""() => {
                let links = Array.from(document.querySelectorAll('a'));
                return links
                    .filter(l => l.href && l.href.endsWith('.pdf'))
                    .map(l => l.href);
            }""")
            
            print(f"\n📄 PDF links found with current logic: {len(pdf_links_current)}")
            for link in pdf_links_current:
                print(f"  - {link}")
            
            # Check for potential PDF links with broader criteria
            potential_pdfs = page.evaluate("""() => {
                let links = Array.from(document.querySelectorAll('a'));
                return links
                    .filter(l => l.href && (
                        l.href.includes('pdf') || 
                        l.href.includes('download') ||
                        l.href.includes('file') ||
                        l.innerText.toLowerCase().includes('pdf') ||
                        l.innerText.toLowerCase().includes('download')
                    ))
                    .map(l => ({
                        href: l.href,
                        text: l.innerText.trim()
                    }));
            }""")
            
            print(f"\n🔍 Potential PDF links (broader search): {len(potential_pdfs)}")
            for link in potential_pdfs:
                print(f"  - {link['text']} -> {link['href']}")
            
            # Check for buttons that might trigger downloads
            buttons = page.evaluate("""() => {
                let buttons = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"]'));
                return buttons.map(b => ({
                    text: b.innerText || b.value || '',
                    className: b.className,
                    id: b.id,
                    type: b.type
                }));
            }""")
            
            print(f"\n🔘 Buttons found: {len(buttons)}")
            for button in buttons[:10]:  # Show first 10
                print(f"  - {button['text']} (type: {button['type']}, class: {button['className']})")
            
            # Check for iframes that might contain PDFs
            iframes = page.evaluate("""() => {
                let iframes = Array.from(document.querySelectorAll('iframe'));
                return iframes.map(i => ({
                    src: i.src,
                    className: i.className,
                    id: i.id
                }));
            }""")
            
            print(f"\n🖼️ Iframes found: {len(iframes)}")
            for iframe in iframes:
                print(f"  - {iframe['src']} (class: {iframe['className']})")
            
            browser.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            browser.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        debug_page(url)
    else:
        # Test with a few example URLs
        test_urls = [
            "https://www.cia.gov/readingroom/document/5076e93d993247d4d82b651b",
            "https://www.cia.gov/readingroom/document/5076e93d993247d4d82b651a",
            "https://www.cia.gov/readingroom/document/5076e93d993247d4d82b6519"
        ]
        
        print("🧪 Testing PDF detection on sample URLs...")
        for url in test_urls:
            debug_page(url)
            print("\n" + "="*80 + "\n") 