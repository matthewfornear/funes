Project Funes

This project scrapes CIA documents from their FOIA reading room and digitizes PDFs using OCR.

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Tesseract OCR:
   - **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - **macOS**: `brew install tesseract`
   - **Linux**: `sudo apt-get install tesseract-ocr`

3. Install Playwright browsers:
```bash
playwright install
```

4. Test your setup:
```bash
python scripts/test_ocr_setup.py
```

## Usage

### Scraping Documents

Start scraping from a specific URL:
```bash
python scripts/collect_articles_continuation.py "https://www.cia.gov/readingroom/search/site?page=173&f%5B0%5D=ds_created%3A%5B2012-01-01T00%3A00%3A00Z%20TO%202013-01-01T00%3A00%3A00Z%5D"
```

Start scraping from a specific year:
```bash
python scripts/collect_articles_continuation.py 2012
```

### OCR Processing

Process all PDFs:
```bash
python scripts/ocr_pdfs.py
```

Show OCR progress:
```bash
python scripts/ocr_pdfs.py progress
```

Retry failed PDFs:
```bash
python scripts/ocr_pdfs.py retry
```

## Directory Structure

```
data/
├── pdfs/          # Input PDFs (from scraping)
├── OCR/           # Output text files (OCR results)
└── metadata/      # Document metadata

settings/
├── ocr_progress.json    # OCR progress tracking
├── visited_urls.json    # Scraping progress
└── scrape_progress.json # Year/page progress
```

## Output Format

Text files in `data/OCR/` contain:
```
filename: document_name.pdf

[OCR text content here]
```

## Features

- **Smart OCR**: Uses PyMuPDF for text extraction first, falls back to OCR if needed
- **Progress Tracking**: Resumes from where it left off
- **Error Handling**: Retry failed documents
- **Rate Limiting Detection**: Automatically detects and handles rate limiting
- **Year Transition**: Automatically moves to next year when current year is complete
- **One-by-One Processing**: Processes files individually with detailed progress updates

## Troubleshooting

If you encounter issues:

1. **Test your setup first:**
   ```bash
   python scripts/test_ocr_setup.py
   ```

2. **Check Tesseract installation:**
   - Windows: Make sure Tesseract is in your PATH
   - macOS/Linux: Verify with `tesseract --version`

3. **Verify PDF directory:**
   - Ensure PDFs are in `data/pdfs/` directory
   - Check file permissions

4. **Check progress:**
   ```bash
   python scripts/ocr_pdfs.py progress
   ``` 