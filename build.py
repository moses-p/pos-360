import os
import shutil
import subprocess
from datetime import datetime

def clean_build():
    """Clean build directories"""
    dirs_to_clean = ['build', 'dist', 'modern_pos.egg-info']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)

def create_directories():
    """Create necessary directories"""
    dirs_to_create = ['dist', 'build']
    for dir_name in dirs_to_create:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

def build_package():
    """Build the package"""
    # Clean previous builds
    clean_build()
    
    # Create directories
    create_directories()
    
    # Build the package
    subprocess.run(['python', 'setup.py', 'sdist', 'bdist_wheel'])
    
    # Create backup of data files
    backup_dir = f"backups/build_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir)
    
    data_files = ['products.json', 'sales_history.json', 'settings.json', 'users.json']
    for file in data_files:
        if os.path.exists(file):
            shutil.copy2(file, backup_dir)
    
    print("Build completed successfully!")
    print(f"Package files are in the 'dist' directory")
    print(f"Data files backed up to {backup_dir}")

if __name__ == "__main__":
    build_package() 