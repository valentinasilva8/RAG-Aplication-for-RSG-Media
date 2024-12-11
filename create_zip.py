import os
import zipfile
from datetime import datetime

def create_zip():
    """Create a zip file of the current directory"""
    try:
        # Get current directory
        current_dir = os.getcwd()
        
        # Create zip filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_name = f"rsg_project_{timestamp}.zip"
        
        # Files and directories to exclude
        exclude = [
            '__pycache__',
            '.git',
            'venv',
            'env',
            'node_modules',
            '.next',
            zip_name,  # Exclude the zip file itself
            '*.pyc',
            '.DS_Store'
        ]
        
        print(f"Creating zip file: {zip_name}")
        print(f"From directory: {current_dir}")
        
        # Create zip file
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(current_dir):
                # Remove excluded directories
                dirs[:] = [d for d in dirs if d not in exclude]
                
                for file in files:
                    # Skip excluded files
                    if any(file.endswith(exc) for exc in ['pyc', 'DS_Store']):
                        continue
                    if file == zip_name:
                        continue
                        
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, current_dir)
                    
                    print(f"Adding: {arcname}")
                    zipf.write(file_path, arcname)
        
        print(f"\nSuccessfully created: {zip_name}")
        print(f"Location: {os.path.abspath(zip_name)}")
        
    except Exception as e:
        print(f"Error creating zip: {str(e)}")

if __name__ == "__main__":
    create_zip()