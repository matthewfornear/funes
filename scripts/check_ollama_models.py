import requests
import json
import subprocess
import sys

def check_ollama_models():
    """Check available Ollama models and suggest the best one for 4070Ti"""
    
    print("🔍 Checking available Ollama models...")
    
    try:
        # Check if Ollama is running
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            print("❌ Ollama is not running. Please start Ollama first.")
            return
        
        models = response.json().get('models', [])
        
        if not models:
            print("❌ No models found. Please install some models first.")
            print("\n💡 Suggested DeepSeek models for 4070Ti:")
            print("   ollama pull deepseek-coder:6.7b")
            print("   ollama pull deepseek-coder:7b")
            print("   ollama pull deepseek-coder:7b-instruct")
            return
        
        print(f"✅ Found {len(models)} models:")
        print()
        
        deepseek_models = []
        other_models = []
        
        for model in models:
            model_name = model['name']
            size = model.get('size', 'Unknown')
            modified = model.get('modified_at', 'Unknown')
            
            if 'deepseek' in model_name.lower():
                deepseek_models.append((model_name, size, modified))
            else:
                other_models.append((model_name, size, modified))
        
        # Show DeepSeek models first
        if deepseek_models:
            print("🤖 DeepSeek Models (Recommended for OCR):")
            for name, size, modified in deepseek_models:
                print(f"   📦 {name}")
                print(f"      Size: {size}")
                print(f"      Modified: {modified}")
                print()
        
        # Show other models
        if other_models:
            print("📦 Other Models:")
            for name, size, modified in other_models:
                print(f"   📦 {name}")
                print(f"      Size: {size}")
                print(f"      Modified: {modified}")
                print()
        
        # Recommendations for 4070Ti
        print("💡 Recommendations for RTX 4070Ti (12GB VRAM):")
        print("   • deepseek-coder:6.7b - Good balance of speed and quality")
        print("   • deepseek-coder:7b - Better quality, slightly slower")
        print("   • deepseek-coder:7b-instruct - Best for instruction following")
        print()
        print("🚀 To install a recommended model:")
        print("   ollama pull deepseek-coder:6.7b")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama. Is it running?")
        print("   Start Ollama with: ollama serve")
    except Exception as e:
        print(f"❌ Error: {e}")

def install_recommended_model():
    """Install the recommended DeepSeek model"""
    print("🚀 Installing recommended DeepSeek model...")
    print("   This may take a while depending on your internet connection.")
    print()
    
    try:
        # Install the recommended model
        result = subprocess.run(
            ["ollama", "pull", "deepseek-coder:6.7b"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Successfully installed deepseek-coder:6.7b")
            print("   You can now run the OCR processing script!")
        else:
            print("❌ Failed to install model:")
            print(result.stderr)
            
    except FileNotFoundError:
        print("❌ Ollama not found. Please install Ollama first:")
        print("   https://ollama.ai/download")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        install_recommended_model()
    else:
        check_ollama_models() 