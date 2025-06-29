import os
import json
import glob
from datetime import datetime

# Configuration - same as original script
SETTINGS_DIR = "settings"
VISITED_LOG = os.path.join(SETTINGS_DIR, "visited_urls.json")
STATUS_LOG = os.path.join(SETTINGS_DIR, "download_status.jsonl")
DATA_DIR = "data"
PDF_DIR = os.path.join(DATA_DIR, "PDFs")
META_DIR = os.path.join(DATA_DIR, "metadata")

def load_visited_urls():
    """Load the list of visited URLs"""
    if os.path.exists(VISITED_LOG):
        with open(VISITED_LOG, "r") as f:
            return set(json.load(f))
    return set()

def load_status_records():
    """Load all status records from the JSONL file"""
    records = []
    if os.path.exists(STATUS_LOG):
        with open(STATUS_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"Warning: Could not parse JSON line: {e}")
    return records

def count_pdf_files():
    """Count actual PDF files in the PDF directory"""
    if os.path.exists(PDF_DIR):
        pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
        return len(pdf_files)
    return 0

def analyze_downloads():
    """Analyze all download data and generate statistics"""
    print("📊 Analyzing CIA document download statistics...")
    print("=" * 60)
    
    # Load data
    visited_urls = load_visited_urls()
    status_records = load_status_records()
    actual_pdf_count = count_pdf_files()
    
    # Calculate statistics
    total_pages_visited = len(visited_urls)
    total_documents_processed = len(status_records)
    
    # Count documents with PDFs
    docs_with_pdfs = 0
    total_pdfs_found = 0
    total_pdfs_downloaded = 0
    
    for record in status_records:
        pdf_urls = record.get('pdf_urls', [])
        downloaded = record.get('downloaded', False)
        downloaded_files = record.get('downloaded_files', [])
        
        if pdf_urls:
            docs_with_pdfs += 1
            total_pdfs_found += len(pdf_urls)
        
        if downloaded:
            total_pdfs_downloaded += len(downloaded_files)
    
    # Calculate percentages
    pct_with_pdfs = (docs_with_pdfs / total_documents_processed * 100) if total_documents_processed > 0 else 0
    pct_downloaded = (total_pdfs_downloaded / total_pdfs_found * 100) if total_pdfs_found > 0 else 0
    
    # Generate report
    report = f"""
CIA Document Download Statistics Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 60}

📄 PAGE STATISTICS:
• Total pages visited: {total_pages_visited:,}
• Total documents processed: {total_documents_processed:,}

📊 PDF STATISTICS:
• Documents with PDFs: {docs_with_pdfs:,}
• Percentage of pages with PDFs: {pct_with_pdfs:.1f}%
• Total PDFs found: {total_pdfs_found:,}
• Total PDFs successfully downloaded: {total_pdfs_downloaded:,}
• Actual PDF files on disk: {actual_pdf_count:,}
• Download success rate: {pct_downloaded:.1f}%

📁 DATA BREAKDOWN:
• Visited URLs stored: {len(visited_urls):,}
• Status records: {len(status_records):,}
• Metadata files: {len(glob.glob(os.path.join(META_DIR, "*.json"))) if os.path.exists(META_DIR) else 0:,}

📈 SUMMARY:
• {pct_with_pdfs:.1f}% of processed documents contain PDFs
• {pct_downloaded:.1f}% of found PDFs were successfully downloaded
• Average PDFs per document (for docs with PDFs): {total_pdfs_found/docs_with_pdfs:.1f if docs_with_pdfs > 0 else 0}
"""
    
    print(report)
    
    # Save report to file
    report_filename = f"download_stats_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"📄 Report saved to: {report_filename}")
    
    # Return statistics for potential further use
    return {
        "total_pages_visited": total_pages_visited,
        "total_documents_processed": total_documents_processed,
        "docs_with_pdfs": docs_with_pdfs,
        "pct_with_pdfs": pct_with_pdfs,
        "total_pdfs_found": total_pdfs_found,
        "total_pdfs_downloaded": total_pdfs_downloaded,
        "actual_pdf_count": actual_pdf_count,
        "pct_downloaded": pct_downloaded
    }

def detailed_analysis():
    """Perform more detailed analysis"""
    print("\n🔍 DETAILED ANALYSIS:")
    print("-" * 40)
    
    status_records = load_status_records()
    
    # Analyze by year (if metadata contains dates)
    year_stats = {}
    for record in status_records:
        metadata = record.get('metadata', {})
        # Look for date fields in metadata
        date_field = None
        for key in ['Date', 'Date Created', 'Creation Date', 'Document Date']:
            if key in metadata:
                date_field = metadata[key]
                break
        
        if date_field:
            try:
                # Try to extract year from various date formats
                import re
                year_match = re.search(r'(\d{4})', date_field)
                if year_match:
                    year = int(year_match.group(1))
                    if year not in year_stats:
                        year_stats[year] = {"total": 0, "with_pdfs": 0}
                    year_stats[year]["total"] += 1
                    if record.get('pdf_urls'):
                        year_stats[year]["with_pdfs"] += 1
            except:
                pass
    
    if year_stats:
        print("📅 Documents by Year:")
        for year in sorted(year_stats.keys()):
            stats = year_stats[year]
            pct = (stats["with_pdfs"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"  {year}: {stats['total']} docs, {stats['with_pdfs']} with PDFs ({pct:.1f}%)")
    
    # Analyze failed downloads
    failed_downloads = []
    for record in status_records:
        if record.get('pdf_urls') and not record.get('downloaded'):
            failed_downloads.append(record.get('url', 'Unknown'))
    
    if failed_downloads:
        print(f"\n❌ Failed Downloads: {len(failed_downloads)}")
        print("First 5 failed URLs:")
        for url in failed_downloads[:5]:
            print(f"  - {url}")

if __name__ == "__main__":
    try:
        stats = analyze_downloads()
        detailed_analysis()
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc() 