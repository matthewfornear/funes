#!/usr/bin/env python3
"""
Installation script for OCR dependencies
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
        print("   Please use Python 3.7 or higher")
        return False

def install_python_packages():
    """Install required Python packages"""
    print("\n📦 Installing Python packages...")
    
    packages = [
        "PyMuPDF==1.23.8",
        "pytesseract==0.3.10", 
        "Pillow==10.1.0",
        "playwright==1.40.0",
        "requests==2.31.0"
    ]
    
    success = True
    for package in packages:
        if not run_command(f"pip install {package}", f"Installing {package}"):
            success = False
    
    return success

def install_playwright_browsers():
    """Install Playwright browsers"""
    print("\n🌐 Installing Playwright browsers...")
    return run_command("playwright install", "Installing Playwright browsers")

def check_tesseract():
    """Check if Tesseract is installed"""
    print("\n🔍 Checking Tesseract OCR...")
    try:
        result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✅ Tesseract - {version}")
            return True
        else:
            print("❌ Tesseract not found")
            return False
    except FileNotFoundError:
        print("❌ Tesseract not installed")
        return False

def create_directories():
    """Create required directories"""
    print("\n📁 Creating directories...")
    
    dirs = [
        "data/pdfs",
        "data/OCR",
        "settings"
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
    print("🚀 OCR Installation Script")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install Python packages
    if not install_python_packages():
        print("\n❌ Failed to install Python packages")
        return False
    
    # Install Playwright browsers
    if not install_playwright_browsers():
        print("\n❌ Failed to install Playwright browsers")
        return False
    
    # Check Tesseract
    tesseract_ok = check_tesseract()
    if not tesseract_ok:
        print("\n⚠️  Tesseract not found!")
        print("   Please install Tesseract OCR:")
        print("   Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        print("   macOS: brew install tesseract")
        print("   Linux: sudo apt-get install tesseract-ocr")
    
    # Create directories
    if not create_directories():
        print("\n❌ Failed to create directories")
        return False
    
    print("\n" + "=" * 50)
    if tesseract_ok:
        print("🎉 Installation complete!")
        print("\nYou can now run:")
        print("  python scripts/test_ocr_setup.py")
        print("  python scripts/ocr_pdfs.py")
    else:
        print("⚠️  Installation mostly complete, but Tesseract is missing.")
        print("   Please install Tesseract OCR to use OCR functionality.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 