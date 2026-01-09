# create_zip_v0_1.py
import zipfile
import os
from datetime import datetime

def create_project_zip(version="0.1"):
    """Create a zip file of the project for a specific version"""
    
    # Define project name and output zip filename
    project_name = "STU_Project"
    zip_filename = f"{project_name}_v{version}_{datetime.now().strftime('%Y%m%d')}.zip"
    
    # List of files to include in the zip (based on your explorer view)
    files_to_include = [
        "conng.py",
        "database.py", 
        "excel_handler.py",
        "main.py",
        "registration.py",
        "test.py"
    ]
    
    # Optional: Include only .py files that actually exist
    existing_files = [f for f in files_to_include if os.path.exists(f)]
    
    print(f"Creating {zip_filename} for version {version}...")
    print(f"Files to include: {existing_files}")
    
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in existing_files:
                if os.path.isfile(file):
                    zipf.write(file)
                    print(f"✓ Added: {file}")
                else:
                    print(f"✗ Skipped (not found): {file}")
            
            # Optional: Add a version info file
            version_info = f"Project: {project_name}\nVersion: {version}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nFiles: {len(existing_files)}"
            zipf.writestr("VERSION_INFO.txt", version_info)
            print("✓ Added: VERSION_INFO.txt")
        
        print(f"\n✅ Successfully created: {zip_filename}")
        print(f"Size: {os.path.getsize(zip_filename) / 1024:.2f} KB")
        
    except Exception as e:
        print(f"❌ Error creating zip: {e}")
        return None
    
    return zip_filename

def create_zip_with_folder_structure(version="0.1"):
    """Alternative: Create zip with folder structure preserved"""
    
    zip_filename = f"STU_Project_Complete_v{version}.zip"
    
    print(f"Creating complete project zip: {zip_filename}")
    
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all Python files in current directory
            for root, dirs, files in os.walk('.'):
                # Skip hidden directories and __pycache__
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, '.')
                        zipf.write(file_path, arcname)
                        print(f"✓ Added: {arcname}")
        
        print(f"\n✅ Complete project zip created: {zip_filename}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    
    return zip_filename

if __name__ == "__main__":
    print("STU Project Zip Creator")
    print("=" * 30)
    
    # Create basic zip with listed files
    print("\n[Option 1: Basic Zip]")
    zip_file1 = create_project_zip("0.1")
    
    # Create complete project zip
    print("\n" + "=" * 30)
    print("[Option 2: Complete Project Zip]")
    choice = input("Create complete project zip with all .py files? (y/n): ")
    
    if choice.lower() == 'y':
        zip_file2 = create_zip_with_folder_structure("0.1")
    
    print("\n" + "=" * 30)
    print("Zip creation complete!")