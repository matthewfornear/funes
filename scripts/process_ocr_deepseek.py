import os
import json
import requests
import time
from pathlib import Path
from typing import List, Dict, Optional

# Configuration
INPUT_DIR = "data/OCR_easyocr"
OUTPUT_DIR = "data/processed_deepseek"
PROGRESS_FILE = "settings/ocr_deepseek_progress.json"
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "deepseek-coder:7b-instruct"  # Best for instruction following and OCR correction

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("settings", exist_ok=True)

def load_progress() -> Dict[str, str]:
    """Load processing progress from file"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_progress(progress: Dict[str, str]):
    """Save processing progress to file"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def check_ollama_model():
    """Check if the specified model is available"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            if MODEL_NAME in model_names:
                print(f"✅ Model {MODEL_NAME} is available")
                return True
            else:
                print(f"❌ Model {MODEL_NAME} not found. Available models:")
                for model in model_names:
                    print(f"  - {model}")
                return False
        else:
            print(f"❌ Failed to connect to Ollama: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error connecting to Ollama: {e}")
        return False

def process_text_with_deepseek(text: str, filename: str) -> Optional[str]:
    """Process OCR text using Ollama DeepSeek model"""
    
    # Create the prompt for OCR correction
    prompt = f"""You are an expert OCR correction assistant. Your task is to fix OCR errors in the following text while preserving ALL original information and meaning. 

IMPORTANT RULES:
1. Fix obvious OCR mistakes (like "€" → "E", "0" → "O", etc.)
2. Correct spacing and formatting issues
3. Fix broken words and sentences
4. Preserve ALL original content - do not add or remove any information
5. Maintain the original document structure and formatting
6. Keep all numbers, dates, names, and technical terms exactly as they should be
7. If you're unsure about a correction, keep the original text

Document: {filename}

OCR Text to correct:
{text}

Corrected text:"""

    try:
        # Prepare the request payload
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent corrections
                "top_p": 0.9,
                "num_predict": 4096
            }
        }
        
        # Make request to Ollama
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=120  # 2 minute timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            corrected_text = result.get('response', '').strip()
            
            # Remove the prompt from the response if it's included
            if "Corrected text:" in corrected_text:
                corrected_text = corrected_text.split("Corrected text:", 1)[1].strip()
            
            return corrected_text
        else:
            print(f"❌ Ollama API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error processing with DeepSeek: {e}")
        return None

def process_file(input_path: str, output_path: str, filename: str) -> bool:
    """Process a single OCR file"""
    try:
        print(f"📄 Processing: {filename}")
        
        # Read the OCR text
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            ocr_text = f.read()
        
        if not ocr_text.strip():
            print(f"⚠️ Empty file: {filename}")
            return False
        
        # Process with DeepSeek
        print(f"🤖 Sending to DeepSeek for OCR correction...")
        corrected_text = process_text_with_deepseek(ocr_text, filename)
        
        if corrected_text is None:
            print(f"❌ Failed to process: {filename}")
            return False
        
        # Save the corrected text
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(corrected_text)
        
        print(f"✅ Saved corrected text: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error processing {filename}: {e}")
        return False

def get_input_files() -> List[str]:
    """Get all OCR files to process"""
    input_files = []
    for file in os.listdir(INPUT_DIR):
        if file.endswith('.txt'):
            input_files.append(file)
    return sorted(input_files)

def main():
    """Main processing function"""
    print("🚀 Starting OCR processing with DeepSeek")
    print(f"📁 Input directory: {INPUT_DIR}")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"🤖 Model: {MODEL_NAME}")
    
    # Check if Ollama and model are available
    if not check_ollama_model():
        print("\n❌ Please install the DeepSeek model first:")
        print(f"   ollama pull {MODEL_NAME}")
        print("\nOr choose a different model by modifying the MODEL_NAME variable.")
        return
    
    # Load progress
    progress = load_progress()
    print(f"📊 Previously processed: {len(progress)} files")
    
    # Get all input files
    input_files = get_input_files()
    print(f"📄 Total files to process: {len(input_files)}")
    
    if not input_files:
        print("❌ No OCR files found in input directory")
        return
    
    # Process files
    processed_count = 0
    failed_count = 0
    
    for filename in input_files:
        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)
        
        # Skip if already processed
        if filename in progress:
            print(f"⏭️ Skipping (already processed): {filename}")
            continue
        
        # Process the file
        success = process_file(input_path, output_path, filename)
        
        if success:
            progress[filename] = "completed"
            processed_count += 1
        else:
            progress[filename] = "failed"
            failed_count += 1
        
        # Save progress after each file
        save_progress(progress)
        
        # Add a small delay to avoid overwhelming the model
        time.sleep(1)
        
        print(f"📊 Progress: {processed_count + failed_count}/{len(input_files)} files")
        print("-" * 50)
    
    # Final summary
    print("\n🎉 Processing complete!")
    print(f"✅ Successfully processed: {processed_count} files")
    print(f"❌ Failed: {failed_count} files")
    print(f"📁 Output saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main() 