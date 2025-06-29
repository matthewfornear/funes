# OCR Processing with DeepSeek

This script processes OCR files from `data/OCR_easyocr` using Ollama with a DeepSeek model to fix OCR errors while preserving all original information.

## Prerequisites

1. **Ollama installed and running**
   - Download from: https://ollama.ai/download
   - Start with: `ollama serve`

2. **A DeepSeek model installed**
   - Recommended for RTX 4070Ti: `deepseek-coder:6.7b`
   - Install with: `ollama pull deepseek-coder:6.7b`

## Quick Start

### 1. Check Available Models
```bash
python scripts/check_ollama_models.py
```

### 2. Install Recommended Model (if needed)
```bash
python scripts/check_ollama_models.py install
```

### 3. Process OCR Files
```bash
python scripts/process_ocr_deepseek.py
```

## How It Works

1. **Input**: Reads OCR text files from `data/OCR_easyocr/`
2. **Processing**: Sends each file to DeepSeek model via Ollama API
3. **Output**: Saves corrected text to `data/processed_deepseek/`
4. **Progress**: Tracks progress in `settings/ocr_deepseek_progress.json`

## OCR Correction Rules

The script instructs the model to:
- Fix obvious OCR mistakes (€ → E, 0 → O, etc.)
- Correct spacing and formatting issues
- Fix broken words and sentences
- **Preserve ALL original information** - no additions or deletions
- Maintain document structure and formatting
- Keep numbers, dates, names, and technical terms accurate

## Model Recommendations for RTX 4070Ti

| Model | Size | Speed | Quality | VRAM Usage |
|-------|------|-------|---------|------------|
| `deepseek-coder:6.7b` | ~4GB | Fast | Good | ~8GB |
| `deepseek-coder:7b` | ~4.5GB | Medium | Better | ~9GB |
| `deepseek-coder:7b-instruct` | ~4.5GB | Medium | Best | ~9GB |

## Configuration

Edit `scripts/process_ocr_deepseek.py` to change:
- `MODEL_NAME`: The Ollama model to use
- `INPUT_DIR`: Source directory for OCR files
- `OUTPUT_DIR`: Destination for processed files
- Processing parameters (temperature, timeout, etc.)

## Troubleshooting

### Ollama Not Running
```bash
ollama serve
```

### Model Not Found
```bash
ollama pull deepseek-coder:6.7b
```

### Out of Memory
- Try a smaller model
- Reduce batch size
- Close other GPU applications

### Slow Processing
- The model processes files sequentially
- Each file takes 30-120 seconds depending on size
- Progress is saved after each file

## File Structure

```
data/
├── OCR_easyocr/           # Input OCR files
├── processed_deepseek/    # Output corrected files
└── settings/
    └── ocr_deepseek_progress.json  # Progress tracking
```

## Example Output

**Before (OCR):**
```
€0 FOR REL€AS€ 
1/16 $20 0 6 
HR 70-14 
```

**After (DeepSeek corrected):**
```
E0 FOR RELEASE 
1/16 1970 06 
HR 70-14 
``` 