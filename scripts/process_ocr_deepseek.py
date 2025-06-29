import os
import json
import requests
import time
import re
from pathlib import Path
from typing import List, Dict, Optional

# Configuration
INPUT_DIR = "data/OCR_easyocr"
OUTPUT_DIR = "data/processed_deepseek"
METADATA_DIR = "data/metadata"
PROGRESS_FILE = "settings/ocr_deepseek_progress.json"
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "deepseek-coder:6.7b-instruct"  # Best for instruction following and OCR correction

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("settings", exist_ok=True)

def load_metadata(filename: str) -> Optional[Dict]:
    """Load metadata for a given file"""
    try:
        # Handle different naming patterns between OCR files and metadata files
        
        # Pattern 1: Try exact match (replace .txt with .json)
        metadata_filename = filename.replace('.txt', '.json')
        metadata_path = os.path.join(METADATA_DIR, metadata_filename)
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            return metadata
        
        # Pattern 2: For specialCollection files, extract collection name
        if 'specialCollection' in filename:
            # Extract collection name from OCR filename
            # Example: specialCollectionSovietandWarsawPact19781978-11-07.pdf__CIA_FOIA_foia.cia.gov_specialCollectionSovietandWarsawPact1978.txt
            # Should match: specialCollectionSovietandWarsawPact1978.json
            
            # Find the collection name (everything after specialCollection and before the date)
            match = re.search(r'specialCollection([^0-9]+)', filename)
            if match:
                collection_name = match.group(1)
                collection_metadata_file = f"specialCollection{collection_name}.json"
                collection_metadata_path = os.path.join(METADATA_DIR, collection_metadata_file)
                
                if os.path.exists(collection_metadata_path):
                    with open(collection_metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    return metadata
        
        # Pattern 3: Try base name without extensions and suffixes
        base_name = filename.split('__')[0] if '__' in filename else filename.replace('.txt', '')
        # Remove any date patterns from the end
        base_name = re.sub(r'\d{4}-\d{2}-\d{2}[a-z]?$', '', base_name)
        base_name = re.sub(r'\d{4}-\d{2}-\d{2}[a-z]?\.pdf$', '', base_name)
        
        alt_metadata_path = os.path.join(METADATA_DIR, f"{base_name}.json")
        
        if os.path.exists(alt_metadata_path):
            with open(alt_metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            return metadata
        
        # Pattern 4: Try to find any metadata file that contains the filename
        for metadata_file in os.listdir(METADATA_DIR):
            if metadata_file.endswith('.json'):
                metadata_path = os.path.join(METADATA_DIR, metadata_file)
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # Check if this metadata file contains info about our file
                    if 'downloaded_files' in metadata:
                        for downloaded_file in metadata['downloaded_files']:
                            if filename.replace('.txt', '.pdf') in downloaded_file:
                                return metadata
                    
                    # Check if title contains our filename
                    if 'title' in metadata and filename.split('__')[0] in metadata['title']:
                        return metadata
                        
                except Exception:
                    continue
        
        return None
    except Exception as e:
        print(f"⚠️ Error loading metadata for {filename}: {e}")
        return None

def extract_publication_date(metadata: Optional[Dict]) -> Optional[str]:
    """Extract publication date from metadata"""
    if not metadata:
        return None
    
    # Try different possible field names
    date_fields = [
        'Publication Date', 'publication_date', 'date', 'Date', 
        'created_date', 'document_date', 'Document Date'
    ]
    
    for field in date_fields:
        if field in metadata:
            date_value = metadata[field]
            if date_value and str(date_value).strip():
                return str(date_value).strip()
    
    return None

def determine_era_from_date(date_str: str) -> Optional[str]:
    """Determine era (decade) from a date string"""
    if not date_str:
        return None
    
    try:
        # Try to extract year from various date formats
        
        # Look for 4-digit year patterns
        year_match = re.search(r'19[7-9]\d|20[0-2]\d', date_str)
        if year_match:
            year = int(year_match.group())
            if 1970 <= year <= 1979:
                return "1970s"
            elif 1980 <= year <= 1989:
                return "1980s"
            elif 1990 <= year <= 1999:
                return "1990s"
            elif 2000 <= year <= 2009:
                return "2000s"
            elif 2010 <= year <= 2019:
                return "2010s"
            elif 2020 <= year <= 2029:
                return "2020s"
        
        return None
    except Exception:
        return None

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

def chunk_text(text, chunk_size=8000, overlap=500):
    """Split text into overlapping chunks for LLM processing."""
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == text_length:
            break
        start = end - overlap  # overlap for context
    return chunks

def process_text_with_deepseek(text: str, filename: str, metadata: Optional[Dict] = None) -> Optional[Dict]:
    """Process OCR text using Ollama DeepSeek model to extract structured data"""
    
    # Extract publication date from metadata
    publication_date = extract_publication_date(metadata)
    era_from_metadata = determine_era_from_date(publication_date) if publication_date else None
    
    # Create the prompt for structured extraction
    prompt = f"""You are an expert document analyzer working for the CIA. Your task is to:
1. Analyze the provided OCR text from CIA documents
2. Extract structured data and keywords based on the content
3. Do NOT return the document text itself - only the metadata and keywords

Document: {filename}
Publication Date (from metadata): {publication_date or "Not available"}
Era from metadata: {era_from_metadata or "Not available"}

OCR Text to analyze:
{text}

Now provide your response in JSON format. Do NOT include the document text in your response - only the metadata fields.

{{
  "filetitle": "The original filename without extension",
  "title": "The document title if present, otherwise null",
  "publication_date": "{publication_date or "null"}",
  "keywords": {{
    "era": "The decade or time period (e.g., 1980s, 1970s, 1990s). Use '{era_from_metadata}' if no date found in document content.",
    "subject_topic": "The primary subject or topic of the document",
    "secondary_topic": "A closely related secondary topic or adjacent field",
    "document_type": "The type of document (e.g., report, memo, analysis, briefing)",
    "geographic_scope": "Geographic regions mentioned or relevant",
    "organizations": "Key organizations, agencies, or institutions mentioned",
    "people": "Important people, leaders, or figures mentioned",
    "technologies": "Technologies, systems, or technical concepts discussed",
    "security_level": "Security classification if mentioned (e.g., SECRET, TOP SECRET, UNCLASSIFIED)",
    "themes": "Recurring themes or concepts in the document"
  }}
}}"""

    try:
        # Prepare the request payload
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent corrections
                "top_p": 0.9,
                "num_predict": 8192  # Increased for longer responses
            }
        }
        
        # Make request to Ollama
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=180  # 3 minute timeout for complex processing
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '').strip()
            
            # Extract JSON from response
            try:
                # Find JSON in the response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    structured_data = json.loads(json_str)
                    
                    # Validate required fields (excluding body)
                    required_fields = ['filetitle', 'keywords']
                    for field in required_fields:
                        if field not in structured_data:
                            print(f"⚠️ Missing required field: {field}")
                            return None
                    
                    # Ensure publication_date is included
                    if 'publication_date' not in structured_data:
                        structured_data['publication_date'] = publication_date
                    
                    # If no era found in document content, use metadata era
                    if era_from_metadata and structured_data.get('keywords', {}).get('era') == 'null':
                        structured_data['keywords']['era'] = era_from_metadata
                    
                    return structured_data
                else:
                    print("❌ No valid JSON found in response")
                    print(f"Response preview: {response_text[:200]}...")
                    return None
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"Response text: {response_text[:500]}...")
                
                # Try to create a basic structure from the response
                try:
                    # Create a basic structure without body
                    structured_data = {
                        "filetitle": filename.replace('.txt', ''),
                        "title": None,
                        "publication_date": publication_date,
                        "keywords": {
                            "era": era_from_metadata or "Unknown",
                            "subject_topic": "Document analysis",
                            "secondary_topic": "OCR correction",
                            "document_type": "Document",
                            "geographic_scope": "Unknown",
                            "organizations": "Unknown",
                            "people": "Unknown",
                            "technologies": "Unknown",
                            "security_level": "Unknown",
                            "themes": "Document processing"
                        }
                    }
                    print("⚠️ Created fallback structure from response")
                    return structured_data
                        
                except Exception as fallback_error:
                    print(f"❌ Fallback processing also failed: {fallback_error}")
                    return None
        else:
            print(f"❌ Ollama API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error processing with DeepSeek: {e}")
        return None

def process_file(input_path: str, output_path: str, filename: str) -> bool:
    """Process a single OCR file with chunking for DeepSeek context window."""
    try:
        print(f"📄 Processing: {filename}")
        
        # Load metadata
        metadata = load_metadata(filename)
        if metadata:
            print(f"   📋 Metadata loaded for: {filename}")
        else:
            print(f"   ⚠️ No metadata found for: {filename}")
        
        # Read the OCR text
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            ocr_text = f.read()
        
        if not ocr_text.strip():
            print(f"⚠️ Empty file: {filename}")
            return False
        
        # Remove filename header from OCR text
        lines = ocr_text.split('\n')
        content_lines = []
        skip_header = True
        
        for line in lines:
            if skip_header and line.startswith('filename:'):
                continue
            elif skip_header and line.strip() == '':
                continue
            elif skip_header:
                skip_header = False
                content_lines.append(line)
            else:
                content_lines.append(line)
        
        # Rejoin the content without the filename header
        clean_ocr_text = '\n'.join(content_lines).strip()
        
        if not clean_ocr_text:
            print(f"⚠️ No content after removing header: {filename}")
            return False
        
        # Chunk the text
        chunks = chunk_text(clean_ocr_text, chunk_size=8000, overlap=500)
        print(f"🔪 Split into {len(chunks)} chunk(s)")
        
        corrected_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"🤖 Sending chunk {i+1}/{len(chunks)} to DeepSeek...")
            # Add chunk info to filename for prompt clarity
            chunk_filename = f"{filename} [chunk {i+1}/{len(chunks)}]"
            structured_data = process_text_with_deepseek(chunk, chunk_filename, metadata)
            if structured_data is None:
                print(f"❌ Failed to process chunk {i+1}/{len(chunks)} of {filename}")
                return False
            corrected_chunks.append(chunk)  # Use the input chunk, not model output
            time.sleep(1)  # avoid overwhelming the model
        
        # Join all input chunks for the final body
        full_body = '\n\n'.join(corrected_chunks)
        # Use the last chunk's structured_data as template for output
        final_structured = structured_data.copy()
        final_structured['body'] = full_body  # Use the input text, not model output
        final_structured['filetitle'] = filename.replace('.txt', '')
        # Save the structured data as JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_structured, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved structured data: {output_path}")
        print(f"   📊 Keywords: {len(final_structured.get('keywords', {}))} fields")
        print(f"   📅 Publication date: {final_structured.get('publication_date', 'Not found')}")
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
    print(f"📁 Metadata directory: {METADATA_DIR}")
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
        output_path = os.path.join(OUTPUT_DIR, filename.replace('.txt', '.json'))
        
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