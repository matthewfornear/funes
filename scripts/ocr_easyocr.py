#!/usr/bin/env python3
"""
OCR script using EasyOCR for comparison with Tesseract
"""

import os
import json
import re
from pathlib import Path
import fitz  # PyMuPDF
import easyocr
from PIL import Image
import io
import time
import numpy as np

# Configuration
PDF_DIR = "data/PDFs"
TEXT_DIR = "data/OCR_easyocr"  # Separate directory for EasyOCR results
SETTINGS_DIR = "settings"
OCR_PROGRESS = os.path.join(SETTINGS_DIR, "ocr_easyocr_progress.json")

# Create directories
os.makedirs(TEXT_DIR, exist_ok=True)
os.makedirs(SETTINGS_DIR, exist_ok=True)

# Initialize EasyOCR reader (only once for performance)
print("🚀 Initializing EasyOCR...")
reader = easyocr.Reader(['en'])  # English only for now
print("✅ EasyOCR initialized")

def save_ocr_progress(filename, status, file_path=None, error_msg=None):
    """Save OCR processing progress with error details"""
    progress = {}
    if os.path.exists(OCR_PROGRESS):
        with open(OCR_PROGRESS, "r") as f:
            progress = json.load(f)
    
    progress[filename] = {
        "status": status,
        "file_path": file_path or os.path.join(PDF_DIR, filename),
        "timestamp": str(Path().cwd()),
        "error": error_msg
    }
    
    with open(OCR_PROGRESS, "w") as f:
        json.dump(progress, f, indent=2)

def get_ocr_progress():
    """Get OCR processing progress"""
    if os.path.exists(OCR_PROGRESS):
        with open(OCR_PROGRESS, "r") as f:
            return json.load(f)
    return {}

def extract_text_robust(page, page_num):
    """Robust text extraction with multiple fallback methods"""
    
    # Method 1: Standard get_text()
    try:
        text = page.get_text()
        if text and text.strip():
            print(f"  📄 Page {page_num + 1}: Text extracted directly ({len(text)} chars)")
            return text
    except Exception as e:
        print(f"  📄 Page {page_num + 1}: Direct extraction failed: {e}")
    
    # Method 2: Try getText() (older PyMuPDF versions)
    try:
        text = page.getText()
        if text and text.strip():
            print(f"  📄 Page {page_num + 1}: Text extracted via getText() ({len(text)} chars)")
            return text
    except Exception as e:
        print(f"  📄 Page {page_num + 1}: getText() failed: {e}")
    
    # Method 3: Extract from text blocks
    try:
        blocks = page.get_text("blocks")
        text_parts = []
        for block in blocks:
            if block[6] == 0:  # Text block
                text_parts.append(block[4])
        
        if text_parts:
            text = "\n".join(text_parts)
            if text.strip():
                print(f"  📄 Page {page_num + 1}: Text extracted from blocks ({len(text)} chars)")
                return text
    except Exception as e:
        print(f"  📄 Page {page_num + 1}: Block extraction failed: {e}")
    
    # Method 4: EasyOCR
    print(f"  📄 Page {page_num + 1}: No text found, attempting EasyOCR...")
    try:
        # Convert page to image with higher resolution
        mat = fitz.Matrix(3, 3)  # Higher resolution for better OCR
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Convert to PIL Image and then to numpy array for EasyOCR
        img = Image.open(io.BytesIO(img_data))
        img_array = np.array(img)
        
        # Perform EasyOCR
        start_time = time.time()
        results = reader.readtext(img_array)
        ocr_time = time.time() - start_time
        
        # Extract text from results
        text_parts = []
        for (bbox, text, confidence) in results:
            text_parts.append(text)
        
        text = "\n".join(text_parts)
        
        if text and text.strip():
            print(f"  📄 Page {page_num + 1}: EasyOCR successful ({len(text)} chars, {len(results)} text blocks, {ocr_time:.2f}s)")
            return text
        else:
            print(f"  📄 Page {page_num + 1}: EasyOCR returned no text")
            return "[EASYOCR FAILED - NO TEXT EXTRACTED]"
        
    except Exception as ocr_error:
        print(f"  📄 Page {page_num + 1}: EasyOCR failed: {ocr_error}")
        return f"[EASYOCR FAILED: {ocr_error}]"

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using multiple methods"""
    try:
        doc = fitz.open(pdf_path)
        text_content = []
        
        print(f"  📊 Processing {len(doc)} pages...")
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = extract_text_robust(page, page_num)
            text_content.append(text)
        
        doc.close()
        
        # Join all pages
        full_text = "\n\n".join(text_content)
        
        # Check if we got any meaningful text - be more lenient
        if full_text.strip():
            # Count non-empty pages
            non_empty_pages = sum(1 for text in text_content if text.strip() and not text.startswith("[EASYOCR FAILED"))
            total_pages = len(text_content)
            
            print(f"  ✅ Successfully extracted {len(full_text)} characters from {non_empty_pages}/{total_pages} pages")
            
            # Accept if we have text from at least 10% of pages or at least 100 characters
            if non_empty_pages > 0 and (non_empty_pages >= total_pages * 0.1 or len(full_text.strip()) >= 100):
                return full_text
            else:
                print(f"  ⚠️ Limited text extracted ({non_empty_pages}/{total_pages} pages, {len(full_text.strip())} chars)")
                return full_text  # Still return it, just warn
        else:
            print(f"  ❌ Failed to extract any text")
            return None
        
    except Exception as e:
        print(f"❌ Error processing PDF {pdf_path}: {e}")
        return None

def process_pdf(pdf_path):
    """Process a single PDF file"""
    filename = os.path.basename(pdf_path)
    text_filename = os.path.splitext(filename)[0] + ".txt"
    text_path = os.path.join(TEXT_DIR, text_filename)
    
    print(f"📄 Processing: {filename}")
    print(f"   📁 Input: {pdf_path}")
    print(f"   📄 Output: {text_path}")
    
    # Check if already processed
    progress = get_ocr_progress()
    if filename in progress and progress[filename]["status"] == "completed":
        print(f"✅ Already processed: {filename}")
        return True
    
    try:
        # Extract text from PDF
        text_content = extract_text_from_pdf(pdf_path)
        
        if text_content is None:
            save_ocr_progress(filename, "failed", pdf_path, "No text extracted")
            return False
        
        # Create output with filename header
        output_content = f"filename: {filename}\n\n{text_content}"
        
        # Save to text file
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(output_content)
        
        print(f"✅ Saved: {text_filename}")
        save_ocr_progress(filename, "completed", pdf_path)
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to process {filename}: {error_msg}")
        save_ocr_progress(filename, "failed", pdf_path, error_msg)
        return False

def backpropagate_completed_files():
    """Mark all .txt files in OCR_easyocr as completed in the progress file if not already marked."""
    progress = get_ocr_progress()
    txt_files = [f for f in os.listdir(TEXT_DIR) if f.endswith('.txt')]
    updated = False
    for txt_file in txt_files:
        # The PDF filename is the .txt filename with .pdf extension
        pdf_filename = txt_file.replace('.txt', '.pdf')
        txt_path = os.path.join(TEXT_DIR, txt_file)
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if content and (pdf_filename not in progress or progress[pdf_filename]["status"] != "completed"):
                progress[pdf_filename] = {
                    "status": "completed",
                    "file_path": os.path.join(PDF_DIR, pdf_filename),
                    "timestamp": str(Path().cwd()),
                    "error": None
                }
                updated = True
        except Exception:
            continue
    if updated:
        with open(OCR_PROGRESS, "w") as f:
            json.dump(progress, f, indent=2)
    return progress

def process_all_pdfs():
    """Process all PDFs in the PDF directory, skipping already completed ones and backpropagating progress."""
    if not os.path.exists(PDF_DIR):
        print(f"❌ PDF directory not found: {PDF_DIR}")
        return
    
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("📭 No PDF files found in the PDF directory")
        return
    
    print(f"📚 Found {len(pdf_files)} PDF files to process")
    
    # Backpropagate progress from existing .txt files
    progress = backpropagate_completed_files()
    completed = [f for f, p in progress.items() if p["status"] == "completed"]
    failed = [f for f, p in progress.items() if p["status"] == "failed"]
    
    print(f"\n📊 Current Progress:")
    print(f"  ✅ Already completed: {len(completed)}")
    print(f"  ❌ Previously failed: {len(failed)}")
    print(f"  🔄 Remaining to process: {len(pdf_files) - len(completed)}")
    
    # Only process files not already completed
    to_process = [f for f in pdf_files if f not in completed]
    
    # Process files one by one
    successful = 0
    failed_count = 0
    
    for i, pdf_file in enumerate(to_process, 1):
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        
        print(f"\n--- Processing file {i}/{len(to_process)} ---")
        
        if process_pdf(pdf_path):
            successful += 1
        else:
            failed_count += 1
        
        print(f"📊 Progress: {i}/{len(to_process)} files processed")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed_count}")
    
    print(f"\n🎉 Processing complete!")
    print(f"📊 Final Results:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed_count}")

def compare_results(pdf_filename):
    """Compare EasyOCR results with Tesseract results for a specific file"""
    tesseract_file = os.path.join("data/OCR", pdf_filename.replace('.pdf', '.txt'))
    easyocr_file = os.path.join(TEXT_DIR, pdf_filename.replace('.pdf', '.txt'))
    
    print(f"🔍 Comparing results for: {pdf_filename}")
    print("=" * 60)
    
    # Read Tesseract results
    tesseract_text = ""
    if os.path.exists(tesseract_file):
        with open(tesseract_file, 'r', encoding='utf-8') as f:
            tesseract_text = f.read()
        print(f"📄 Tesseract file: {len(tesseract_text)} characters")
    else:
        print("❌ Tesseract file not found")
    
    # Read EasyOCR results
    easyocr_text = ""
    if os.path.exists(easyocr_file):
        with open(easyocr_file, 'r', encoding='utf-8') as f:
            easyocr_text = f.read()
        print(f"📄 EasyOCR file: {len(easyocr_text)} characters")
    else:
        print("❌ EasyOCR file not found")
    
    if tesseract_text and easyocr_text:
        # Remove filename headers for comparison
        tesseract_clean = tesseract_text.split('\n\n', 1)[-1] if '\n\n' in tesseract_text else tesseract_text
        easyocr_clean = easyocr_text.split('\n\n', 1)[-1] if '\n\n' in easyocr_text else easyocr_text
        
        print(f"\n📊 Comparison:")
        print(f"  Tesseract: {len(tesseract_clean)} characters")
        print(f"  EasyOCR:   {len(easyocr_clean)} characters")
        print(f"  Difference: {abs(len(tesseract_clean) - len(easyocr_clean))} characters")
        
        # Show first 200 characters of each
        print(f"\n📝 Tesseract (first 200 chars):")
        print(repr(tesseract_clean[:200]))
        print(f"\n📝 EasyOCR (first 200 chars):")
        print(repr(easyocr_clean[:200]))

def process_single_pdf(pdf_filename):
    """Process a single PDF file by name"""
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    if os.path.exists(pdf_path):
        return process_pdf(pdf_path)
    else:
        print(f"❌ File not found: {pdf_path}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "compare" and len(sys.argv) > 2:
            compare_results(sys.argv[2])
        elif command == "single" and len(sys.argv) > 2:
            process_single_pdf(sys.argv[2])
        elif command == "retry":
            # Retry failed files
            progress = get_ocr_progress()
            failed = [f for f, p in progress.items() if p["status"] == "failed"]
            
            if not failed:
                print("📭 No failed files to retry")
                sys.exit(0)
            
            print(f"🔄 Retrying {len(failed)} failed files...")
            for filename in failed:
                file_path = progress[filename].get("file_path", os.path.join(PDF_DIR, filename))
                if os.path.exists(file_path):
                    process_pdf(file_path)
        else:
            print("Usage: python scripts/ocr_easyocr.py [compare|single|retry] [filename]")
            print("  compare <filename>: Compare EasyOCR vs Tesseract results")
            print("  single <filename>: Process a single PDF file")
            print("  retry: Retry failed PDFs")
            print("  (no args): Process all PDFs")
    else:
        process_all_pdfs() 