#!/usr/bin/env python3
"""
Improved OCR script with better text extraction and error handling
"""

import os
import json
import re
from pathlib import Path
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

# Configuration
PDF_DIR = "data/PDFs"  # Fixed to match actual directory
TEXT_DIR = "data/OCR"
SETTINGS_DIR = "settings"
OCR_PROGRESS = os.path.join(SETTINGS_DIR, "ocr_progress.json")

# Create directories
os.makedirs(TEXT_DIR, exist_ok=True)
os.makedirs(SETTINGS_DIR, exist_ok=True)

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
    text_content = []
    
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
    
    # Method 4: OCR
    print(f"  📄 Page {page_num + 1}: No text found, attempting OCR...")
    try:
        # Convert page to image with higher resolution
        mat = fitz.Matrix(3, 3)  # Even higher resolution
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Convert to PIL Image
        img = Image.open(io.BytesIO(img_data))
        
        # Try different OCR configurations
        ocr_configs = [
            '--oem 3 --psm 6',  # Default
            '--oem 3 --psm 3',  # Fully automatic page segmentation
            '--oem 1 --psm 6',  # Legacy engine
            '--oem 3 --psm 1',  # Automatic page segmentation with OSD
        ]
        
        for i, config in enumerate(ocr_configs):
            try:
                text = pytesseract.image_to_string(img, config=config)
                if text and text.strip():
                    print(f"  📄 Page {page_num + 1}: OCR successful with config {i+1} ({len(text)} chars)")
                    return text
            except Exception as ocr_error:
                print(f"  📄 Page {page_num + 1}: OCR config {i+1} failed: {ocr_error}")
                continue
        
        print(f"  📄 Page {page_num + 1}: All OCR methods failed")
        return "[OCR FAILED - NO TEXT EXTRACTED]"
        
    except Exception as ocr_error:
        print(f"  📄 Page {page_num + 1}: OCR setup failed: {ocr_error}")
        return f"[OCR SETUP FAILED: {ocr_error}]"

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
        
        # Check if we got any meaningful text
        if full_text.strip() and not full_text.startswith("[OCR FAILED") and not full_text.startswith("[OCR SETUP FAILED"):
            print(f"  ✅ Successfully extracted {len(full_text)} characters")
            return full_text
        else:
            print(f"  ❌ Failed to extract meaningful text")
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

def process_all_pdfs():
    """Process all PDFs in the PDF directory"""
    if not os.path.exists(PDF_DIR):
        print(f"❌ PDF directory not found: {PDF_DIR}")
        return
    
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("📭 No PDF files found in the PDF directory")
        return
    
    print(f"📚 Found {len(pdf_files)} PDF files to process")
    
    # Load progress
    progress = get_ocr_progress()
    completed = [f for f, p in progress.items() if p["status"] == "completed"]
    failed = [f for f, p in progress.items() if p["status"] == "failed"]
    
    print(f"\n📊 Current Progress:")
    print(f"  ✅ Already completed: {len(completed)}")
    print(f"  ❌ Previously failed: {len(failed)}")
    print(f"  🔄 Remaining to process: {len(pdf_files) - len(completed)}")
    
    # Process files one by one
    successful = 0
    failed_count = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        
        print(f"\n--- Processing file {i}/{len(pdf_files)} ---")
        
        if process_pdf(pdf_path):
            successful += 1
        else:
            failed_count += 1
        
        print(f"📊 Progress: {i}/{len(pdf_files)} files processed")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed_count}")
    
    print(f"\n🎉 Processing complete!")
    print(f"📊 Final Results:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed_count}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "retry":
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
            print("Usage: python scripts/ocr_pdfs_improved.py [retry]")
    else:
        process_all_pdfs() 