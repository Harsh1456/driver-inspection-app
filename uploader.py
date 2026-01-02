import os
import uuid
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
from PIL import Image
import logging
import subprocess

logger = logging.getLogger(__name__)

class FileUploader:
    """Handles file uploads and processing"""
    
    def __init__(self, upload_folder, allowed_extensions):
        self.upload_folder = upload_folder
        self.allowed_extensions = allowed_extensions
        os.makedirs(upload_folder, exist_ok=True)
    
    def allowed_file(self, filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def save_uploaded_file(self, file):
        try:
            if file and self.allowed_file(file.filename):
                file_id = str(uuid.uuid4())
                original_filename = secure_filename(file.filename)
                file_extension = original_filename.rsplit('.', 1)[1].lower()
                saved_filename = f"{file_id}.{file_extension}"
                file_path = os.path.join(self.upload_folder, saved_filename)
                
                file.save(file_path)
                os.chmod(file_path, 0o644)
                
                return {
                    'success': True,
                    'file_id': file_id,
                    'original_filename': original_filename,
                    'saved_filename': saved_filename,
                    'file_path': file_path,
                    'file_type': file_extension
                }
            else:
                return {'success': False, 'error': 'Invalid file type'}
                
        except Exception as e:
            logger.error(f"Error saving uploaded file: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def convert_pdf_to_images(self, pdf_path, output_dir):
        try:
            # Check if PDF exists
            if not os.path.exists(pdf_path):
                return []
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            os.chmod(output_dir, 0o755)
            
            print(f"Converting PDF: {pdf_path}")
            
            # Simple conversion with error handling
            images = convert_from_path(pdf_path, dpi=200)
            image_paths = []
            
            for i, image in enumerate(images):
                image_filename = f"page_{i+1}.jpg"
                image_path = os.path.join(output_dir, image_filename)
                
                if image.mode in ('RGBA', 'P'):
                    image = image.convert('RGB')
                
                image.save(image_path, 'JPEG', quality=85)
                os.chmod(image_path, 0o644)
                image_paths.append(image_path)
                print(f"Created image: {image_path}")
            
            return image_paths
            
        except Exception as e:
            print(f"PDF conversion error: {str(e)}")
            return []
    
    def process_single_image(self, image_path, output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
            os.chmod(output_dir, 0o755)
            
            with Image.open(image_path) as image:
                if image.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = background
                elif image.mode != 'RGB':
                    image = image.convert('RGB')
                
                output_path = os.path.join(output_dir, "page_1.jpg")
                image.save(output_path, 'JPEG', quality=85)
                os.chmod(output_path, 0o644)
            
            return [output_path]
            
        except Exception as e:
            print(f"Image processing error: {str(e)}")
            return []
