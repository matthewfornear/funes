#!/usr/bin/env python3
"""
Installation script for EasyOCR
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 7:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - TOO OLD")
        print("   EasyOCR requires Python 3.7 or higher")
        return False

def install_easyocr():
    """Install EasyOCR and its dependencies"""
    print("\n📦 Installing EasyOCR...")
    
    # EasyOCR has many dependencies, install them step by step
    packages = [
        "easyocr==1.7.0",
        "torch==2.1.0",  # PyTorch for EasyOCR
        "torchvision==0.16.0",
        "opencv-python==4.8.1.78",
        "numpy==1.24.3",
        "Pillow==10.1.0",
        "scipy==1.11.4",
        "scikit-image==0.21.0"
    ]
    
    success = True
    for package in packages:
        if not run_command(f"pip install {package}", f"Installing {package}"):
            success = False
            print(f"⚠️ Failed to install {package}, but continuing...")
    
    return success

def test_easyocr():
    """Test if EasyOCR is working"""
    print("\n🧪 Testing EasyOCR installation...")
    try:
        import easyocr
        print("✅ EasyOCR import successful")
        
        # Test initialization
        print("🔄 Testing EasyOCR initialization...")
        reader = easyocr.Reader(['en'])
        print("✅ EasyOCR initialization successful")
        
        return True
    except Exception as e:
        print(f"❌ EasyOCR test failed: {e}")
        return False

def create_directories():
    """Create required directories"""
    print("\n📁 Creating directories...")
    
    dirs = [
        "data/OCR_easyocr"
    ]
    
    for dir_path in dirs:
        try:
            os.makedirs(dir_path, exist_ok=True)
            print(f"✅ Created: {dir_path}")
        except Exception as e:
            print(f"❌ Failed to create {dir_path}: {e}")
            return False
    
    return True

def main():
    """Main installation process"""
    print("🚀 EasyOCR Installation Script")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install EasyOCR
    if not install_easyocr():
        print("\n❌ Failed to install EasyOCR")
        return False
    
    # Test EasyOCR
    if not test_easyocr():
        print("\n❌ EasyOCR test failed")
        return False
    
    # Create directories
    if not create_directories():
        print("\n❌ Failed to create directories")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 EasyOCR installation complete!")
    print("\nYou can now run:")
    print("  python scripts/ocr_easyocr.py")
    print("  python scripts/ocr_easyocr.py single <filename>")
    print("  python scripts/ocr_easyocr.py compare <filename>")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 