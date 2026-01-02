import os
import uuid
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
from PIL import Image
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class FileUploader:
    """Handles file uploads and processing"""
    
    def __init__(self, upload_folder, allowed_extensions):
        """
        Initialize file uploader
        
        Args:
            upload_folder (str): Directory to store uploaded files
            allowed_extensions (set): Set of allowed file extensions
        """
        self.upload_folder = upload_folder
        self.allowed_extensions = allowed_extensions
        
        # Create upload directory if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)
    
    def allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def save_uploaded_file(self, file):
        """
        Save uploaded file to disk
        
        Args:
            file: Werkzeug FileStorage object
            
        Returns:
            dict: File info including saved path
        """
        try:
            if file and self.allowed_file(file.filename):
                # Generate unique filename
                file_id = str(uuid.uuid4())
                original_filename = secure_filename(file.filename)
                file_extension = original_filename.rsplit('.', 1)[1].lower()
                saved_filename = f"{file_id}.{file_extension}"
                file_path = os.path.join(self.upload_folder, saved_filename)
                
                # Save file
                file.save(file_path)
                
                return {
                    'success': True,
                    'file_id': file_id,
                    'original_filename': original_filename,
                    'saved_filename': saved_filename,
                    'file_path': file_path,
                    'file_type': file_extension
                }
            else:
                return {
                    'success': False,
                    'error': 'Invalid file type'
                }
                
        except Exception as e:
            logger.error(f"Error saving uploaded file: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def convert_pdf_to_images(self, pdf_path, output_dir):
        """
        Convert PDF pages to images
        
        Args:
            pdf_path (str): Path to PDF file
            output_dir (str): Directory to save converted images
            
        Returns:
            list: List of saved image paths
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Convert PDF to images with error handling
            images = convert_from_path(pdf_path, dpi=200)
            image_paths = []
            
            for i, image in enumerate(images):
                image_filename = f"page_{i+1}.jpg"
                image_path = os.path.join(output_dir, image_filename)
                
                # Convert to RGB if necessary (for JPEG compatibility)
                if image.mode in ('RGBA', 'P'):
                    image = image.convert('RGB')
                
                image.save(image_path, 'JPEG', quality=85)
                image_paths.append(image_path)
            
            return image_paths
            
        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            return []
    
    def process_single_image(self, image_path, output_dir):
        """
        Process single image file (for non-PDF uploads)
        
        Args:
            image_path (str): Path to image file
            output_dir (str): Directory to save processed image
            
        Returns:
            list: List containing single image path
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Open and process the image
            with Image.open(image_path) as image:
                # Convert to RGB if the image has transparency (RGBA, LA, etc.)
                if image.mode in ('RGBA', 'LA', 'P'):
                    # Create a white background
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    # Paste the image onto the white background
                    background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = background
                elif image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # For single images, we still create a page_1.jpg for consistency
                output_path = os.path.join(output_dir, "page_1.jpg")
                image.save(output_path, 'JPEG', quality=85)
            
            return [output_path]
            
        except Exception as e:
            logger.error(f"Error processing single image: {str(e)}")
            return []
