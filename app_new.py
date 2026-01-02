from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
import os
import uuid
import json
from datetime import datetime
from werkzeug.utils import secure_filename

# Import modules
from config import Config
from database import db, UploadedFile, ReportPage
from uploader import FileUploader
from classifier import RemarkClassifier
from extractor import TextExtractor
from dashboard import dashboard_bp

# Set Ultralytics cache directory before importing YOLO
os.environ['ULTRALYTICS_HOME'] = '/home/ubuntu/driver-inspection-app/ultralytics_cache'

# Initialize Flask app
app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static',
            template_folder='templates')
app.config.from_object(Config)

# Initialize components
db.init_app(app)
file_uploader = FileUploader(app.config['UPLOAD_FOLDER'], app.config['ALLOWED_EXTENSIONS'])

# Initialize AI components
classifier = None
text_extractor = None

try:
    classifier = RemarkClassifier(app.config['YOLO_MODEL_PATH'])
    print("✓ YOLO classifier loaded successfully")
except Exception as e:
    print(f"✗ YOLO classifier failed: {e}")
    classifier = None

try:
    api_key = app.config.get('OPENAI_API_KEY')
    if api_key and api_key.strip() and not api_key.startswith('your-openai-api-key'):
        text_extractor = TextExtractor(api_key)
        print("✓ Text extractor initialized successfully")
    else:
        print("✗ OpenAI API key not configured properly")
        text_extractor = None
except Exception as e:
    print(f"✗ Text extractor failed: {e}")
    text_extractor = None

# Register blueprints
app.register_blueprint(dashboard_bp)

# Explicit static file route (as backup)
@app.route('/static/<path:filename>')
def custom_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/')
def home():
    """Home page"""
    return render_template('index.html')

@app.route('/upload')
def upload_page():
    """File upload interface"""
    return render_template('upload.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """API endpoint for file upload and processing"""
    try:
        print("Upload endpoint hit")  # Debug log
        if 'file' not in request.files:
            print("No file in request")
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            print("Empty filename")
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        print(f"Processing file: {file.filename}")
        
        # Check if AI components are available
        if classifier is None:
            print("Classifier not available")
            return jsonify({'success': False, 'error': 'YOLO classifier not available'}), 500
        if text_extractor is None:
            print("Text extractor not available")
            return jsonify({'success': False, 'error': 'Text extractor not available. Please check OpenAI API key configuration.'}), 500
        
        # Save uploaded file
        save_result = file_uploader.save_uploaded_file(file)
        if not save_result['success']:
            print(f"Save failed: {save_result['error']}")
            return jsonify({'success': False, 'error': save_result['error']}), 400
        
        print(f"File saved successfully: {save_result['file_id']}")
        
        # Process the file
        process_result = process_uploaded_file(save_result)
        print(f"Processing result: {process_result}")
        
        return jsonify(process_result)
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def process_uploaded_file(file_info):
    """
    Process uploaded file through classification and extraction pipeline with batching
    """
    file_id = file_info['file_id']
    file_path = file_info['file_path']
    file_type = file_info['file_type']
    
    try:
        # Create file record in database
        file_record = UploadedFile(
            file_id=file_id,
            file_name=file_info['original_filename'],
            file_type=file_type,
            file_path=file_path
        )
        db.session.add(file_record)
        
        # Convert file to images
        images_dir = os.path.join(app.config['UPLOAD_FOLDER'], file_id)
        image_paths = []
        
        print(f"Converting {file_type} file to images...")
        
        if file_type.lower() == 'pdf':
            image_paths = file_uploader.convert_pdf_to_images(file_path, images_dir)
            print(f"PDF conversion result: {len(image_paths)} images created")
        else:
            image_paths = file_uploader.process_single_image(file_path, images_dir)
            print(f"Image processing result: {len(image_paths)} images created")
        
        if not image_paths:
            error_msg = f"Failed to convert {file_type} to images. "
            if file_type.lower() == 'pdf':
                error_msg += "Please ensure poppler-utils is installed and the PDF file is valid."
            else:
                error_msg += "Please check if the image file is valid."
            print(error_msg)
            raise Exception(error_msg)
        
        # Process each page - FIRST PASS: Only classification
        pages_data = []
        pages_with_remarks = 0
        
        for i, image_path in enumerate(image_paths):
            page_id = str(uuid.uuid4())
            
            # Classify page
            classification_result = classifier.classify_image(image_path)
            
            has_remarks = classification_result['has_remarks']
            confidence = classification_result['confidence']
            bounding_boxes = classification_result['bounding_boxes']
            
            if has_remarks:
                pages_with_remarks += 1
            
            # Store page data for batch processing
            pages_data.append({
                'page_id': page_id,
                'page_number': i + 1,
                'image_path': image_path,
                'has_remarks': has_remarks,
                'confidence': confidence,
                'bounding_boxes': bounding_boxes,
                'extracted_text': "",
                'original_text': "",  # Store original extracted text
                'extraction_confidence': 0.0,
                'correction_applied': False  # Track if correction was applied
            })
        
        # SECOND PASS: Batch text extraction for pages with remarks
        if pages_with_remarks > 0:
            print(f"Batch processing {pages_with_remarks} pages with remarks...")
            
            # Extract all remark regions first
            remark_images = []
            remark_page_indices = []
            
            for i, page_data in enumerate(pages_data):
                if page_data['has_remarks']:
                    remarks_image = classifier.extract_remarks_region(
                        page_data['image_path'], 
                        page_data['bounding_boxes']
                    )
                    if remarks_image:
                        remark_images.append(remarks_image)
                        remark_page_indices.append(i)
            
            # Batch extract text from all remark images
            if remark_images:
                batch_result = text_extractor.batch_extract_text_from_images(remark_images)
                
                # Update pages with extracted text
                for idx, page_index in enumerate(remark_page_indices):
                    if idx < len(batch_result['texts']):
                        extracted_text = batch_result['texts'][idx]
                        correction_applied = batch_result.get('correction_applied', [False] * len(batch_result['texts']))[idx]
                        improvement_score = batch_result.get('improvement_scores', [0.0] * len(batch_result['texts']))[idx]
                        
                        # If batch extraction returned "NO_HANDWRITING_DETECTED" but we know there are remarks,
                        # try individual extraction as fallback
                        if extracted_text == "NO_HANDWRITING_DETECTED":
                            print(f"Batch extraction failed for page {pages_data[page_index]['page_number']}, trying individual extraction...")
                            individual_result = text_extractor.extract_text_from_image(remark_images[idx])
                            if individual_result['success'] and individual_result['text'] != "NO_HANDWRITING_DETECTED":
                                pages_data[page_index]['extracted_text'] = individual_result.get('corrected_text', individual_result['text'])
                                pages_data[page_index]['original_text'] = individual_result['text']
                                pages_data[page_index]['extraction_confidence'] = individual_result['confidence']
                                pages_data[page_index]['correction_applied'] = individual_result.get('correction_applied', False)
                                pages_data[page_index]['improvement_score'] = individual_result.get('improvement_score', 0.0)
                            else:
                                pages_data[page_index]['extracted_text'] = "Unable to extract text"
                                pages_data[page_index]['extraction_confidence'] = 0.0
                        else:
                            pages_data[page_index]['extracted_text'] = extracted_text
                            pages_data[page_index]['original_text'] = batch_result.get('original_texts', [extracted_text] * len(batch_result['texts']))[idx]
                            pages_data[page_index]['extraction_confidence'] = batch_result['confidences'][idx]
                            pages_data[page_index]['correction_applied'] = correction_applied
                            pages_data[page_index]['improvement_score'] = improvement_score
        
        # Create database records
        pages_without_remarks = len(image_paths) - pages_with_remarks
        
        for page_data in pages_data:
            page_record = ReportPage(
                page_id=page_data['page_id'],
                file_id=file_id,
                page_number=page_data['page_number'],
                has_remarks=page_data['has_remarks'],
                extracted_text=page_data['extracted_text'],  # This will now store corrected text
                original_text=page_data.get('original_text', page_data['extracted_text']),  # Store original
                correction_applied=page_data.get('correction_applied', False),  # Track correction
                improvement_score=page_data.get('improvement_score', 0.0),  # Store improvement score
                confidence_score=page_data['extraction_confidence'] if page_data['has_remarks'] else page_data['confidence'],
                image_path=page_data['image_path'],
                bounding_boxes=json.dumps(page_data['bounding_boxes'])
            )
            db.session.add(page_record)
        
        # Calculate criticality
        total_pages = len(image_paths)
        if total_pages > 0:
            remarks_percentage = (pages_with_remarks / total_pages) * 100
            
            if remarks_percentage > 60:
                criticality = 'RED'
            elif remarks_percentage > 30:
                criticality = 'ORANGE'
            else:
                criticality = 'GREEN'
        else:
            criticality = 'GREEN'
        
        # Update file record with processing results
        file_record.total_pages = total_pages
        file_record.pages_with_remarks = pages_with_remarks
        file_record.pages_without_remarks = pages_without_remarks
        file_record.criticality_level = criticality
        
        # Commit all changes
        db.session.commit()
        
        return {
            'success': True,
            'file_id': file_id,
            'total_pages': total_pages,
            'pages_with_remarks': pages_with_remarks,
            'criticality': criticality,
            'message': 'File processed successfully'
        }
        
    except Exception as e:
        db.session.rollback()
        print(f"Error processing file: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/image/<file_id>/<int:page_number>')
def serve_image(file_id, page_number):
    """Serve images"""
    try:
        # Get page from database
        page = ReportPage.query.filter_by(file_id=file_id, page_number=page_number).first()
        if not page or not page.image_path:
            return "Image not found", 404
        
        # Check if image file exists
        if not os.path.exists(page.image_path):
            return "Image file not found", 404
            
        return send_file(page.image_path)
        
    except Exception as e:
        print(f"Image serve error: {e}")
        return "Image not found", 404

@app.route('/api/file/<file_id>/delete', methods=['DELETE'])
def delete_file(file_id):
    """Delete a file and all its associated images"""
    try:
        file = UploadedFile.query.get_or_404(file_id)
        
        # Delete associated images from filesystem
        for page in file.pages:
            if page.image_path and os.path.exists(page.image_path):
                try:
                    os.remove(page.image_path)
                except Exception:
                    pass
        
        # Delete the directory if empty
        file_dir = os.path.join(app.config['UPLOAD_FOLDER'], file_id)
        if os.path.exists(file_dir) and os.path.isdir(file_dir):
            try:
                if not os.listdir(file_dir):
                    os.rmdir(file_dir)
            except Exception:
                pass
        
        # Delete database records
        ReportPage.query.filter_by(file_id=file_id).delete()
        db.session.delete(file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'File and associated images deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting file: {str(e)}'
        }), 500

@app.route('/api/page/<page_id>/update-text', methods=['POST'])
def update_page_text(page_id):
    """Update extracted text for a page"""
    try:
        page = ReportPage.query.get_or_404(page_id)
        new_text = request.json.get('text', '')
        
        page.extracted_text = new_text
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Text updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating text: {str(e)}'
        }), 500

@app.route('/test')
def test_route():
    """Test route to check if everything is working"""
    return jsonify({
        'status': 'working',
        'static_files': os.path.exists(app.static_folder),
        'templates': os.path.exists(app.template_folder),
        'classifier_loaded': classifier is not None,
        'text_extractor_loaded': text_extractor is not None,
        'upload_folder': os.path.exists(app.config['UPLOAD_FOLDER']),
        'database_connected': True
    })

# Create tables when app starts
with app.app_context():
    try:
        db.create_all()
        print("✓ Database tables created successfully")
    except Exception as e:
        print(f"✗ Database creation failed: {e}")

if __name__ == '__main__':
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    print("Starting server on http://localhost:5000")
    print(f"Static folder: {app.static_folder}")
    print(f"Template folder: {app.template_folder}")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    # Run the app with clean logs
    app.run(debug=True, host='0.0.0.0', port=5000)
