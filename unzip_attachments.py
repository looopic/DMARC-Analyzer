import os
import zipfile
import gzip
import shutil

def unzip_files(source_directory, target_directory):
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
    
    for filename in os.listdir(source_directory):
        file_path = os.path.join(source_directory, filename)
        
        if filename.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_directory)
            os.remove(file_path)
            print(f'Unzipped and deleted: {filename}')
        
        elif filename.endswith('.gz'):
            with gzip.open(file_path, 'rb') as f_in:
                with open(os.path.join(target_directory, filename[:-3]), 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(file_path)
            print(f'Extracted and deleted: {filename}')

if __name__ == "__main__":
    unzip_files('./downloaded_mails', './extracted_files')