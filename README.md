Project Funes

This project scrapes CIA documents from their FOIA reading room and digitizes PDFs using OCR with EasyOCR and DeepSeek AI correction.

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install EasyOCR (replaces Tesseract):
```bash
pip install easyocr
```

3. Install Ollama for DeepSeek AI processing:
   - **Windows/macOS/Linux**: Download from https://ollama.ai/
   - Install the DeepSeek model:
   ```bash
   ollama pull deepseek-coder:6.7b-instruct
   ```

4. Install Playwright browsers:
```bash
playwright install
```

5. Test your setup:
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

#### Basic OCR with EasyOCR

Process all PDFs using EasyOCR:
```bash
python scripts/ocr_easyocr.py
```

Show OCR progress:
```bash
python scripts/ocr_easyocr.py progress
```

Retry failed PDFs:
```bash
python scripts/ocr_easyocr.py retry
```

#### Advanced OCR with DeepSeek AI Correction

Process OCR files with DeepSeek AI for correction and metadata extraction:
```bash
python scripts/process_ocr_deepseek.py
```

This script:
- Chunks large documents to fit within DeepSeek's context window
- Extracts structured metadata (keywords, topics, organizations, etc.)
- Preserves the complete original document text
- Outputs JSON files with both document content and AI-generated metadata

## Directory Structure

```
data/
├── PDFs/                    # Input PDFs (from scraping)
├── OCR_easyocr/            # Output text files (EasyOCR results)
├── processed_deepseek/     # AI-processed JSON files with metadata
└── metadata/               # Document metadata

settings/
├── ocr_progress.json       # OCR progress tracking
├── ocr_deepseek_progress.json # DeepSeek processing progress
├── visited_urls.json       # Scraping progress
└── scrape_progress.json    # Year/page progress
```

## Output Format

### EasyOCR Output
Text files in `data/OCR_easyocr/` contain:
```
filename: document_name.pdf

[OCR text content here]
```

### DeepSeek Output
JSON files in `data/processed_deepseek/` contain:
```json
{
  "filetitle": "document_name",
  "title": "Document title if found",
  "body": "Complete document text content",
  "publication_date": "Date from metadata",
  "keywords": {
    "era": "1950s",
    "subject_topic": "Intelligence",
    "secondary_topic": "Foreign Affairs",
    "document_type": "Report",
    "geographic_scope": "USSR, USA",
    "organizations": "CIA, KGB",
    "people": "Key figures mentioned",
    "technologies": "Technologies discussed",
    "security_level": "SECRET",
    "themes": "Recurring themes"
  }
}
```

## Features

- **EasyOCR Integration**: Uses EasyOCR for high-quality text extraction
- **DeepSeek AI Processing**: Advanced OCR correction and metadata extraction
- **Smart Chunking**: Handles large documents by splitting into manageable chunks
- **Progress Tracking**: Resumes from where it left off
- **Error Handling**: Retry failed documents
- **Rate Limiting Detection**: Automatically detects and handles rate limiting
- **Year Transition**: Automatically moves to next year when current year is complete
- **One-by-One Processing**: Processes files individually with detailed progress updates
- **Metadata Integration**: Combines scraping metadata with AI-generated insights

## Troubleshooting

If you encounter issues:

1. **Test your setup first:**
   ```bash
   python scripts/test_ocr_setup.py
   ```

2. **Check EasyOCR installation:**
   ```bash
   python -c "import easyocr; print('EasyOCR installed successfully')"
   ```

3. **Check Ollama and DeepSeek:**
   ```bash
   ollama list
   ```
   Make sure `deepseek-coder:6.7b-instruct` is available.

4. **Verify PDF directory:**
   - Ensure PDFs are in `data/PDFs/` directory
   - Check file permissions

5. **Check progress:**
   ```bash
   python scripts/ocr_easyocr.py progress
   python scripts/process_ocr_deepseek.py
   ``` 