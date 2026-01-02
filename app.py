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

import traceback

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


@app.route('/debug/db-status')
def debug_db_status():
    """Check database connection and contents"""
    try:
        # Test database connection - FIXED for SQLAlchemy 2.0
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        
        # Get all files
        files = UploadedFile.query.all()
        files_data = []
        
        for file in files:
            pages = ReportPage.query.filter_by(file_id=file.file_id).all()
            files_data.append({
                'file_id': file.file_id,
                'file_name': file.file_name,
                'upload_time': file.upload_timestamp.isoformat() if file.upload_timestamp else None,
                'total_pages': file.total_pages,
                'pages_in_db': len(pages),
                'file_exists': os.path.exists(file.file_path) if file.file_path else False
            })
        
        return jsonify({
            'database_connected': True,
            'total_files': len(files),
            'files': files_data
        })
        
    except Exception as e:
        return jsonify({
            'database_connected': False,
            'error': str(e)
        })


@app.route('/debug/real-time-db')
def real_time_db():
    """Real-time database monitoring"""
    from sqlalchemy import text
    
    try:
        # Test connection
        db.session.execute(text('SELECT 1'))
        
        # Get immediate counts
        files_count = UploadedFile.query.count()
        pages_count = ReportPage.query.count()
        
        # Get latest files
        latest_files = UploadedFile.query.order_by(UploadedFile.upload_timestamp.desc()).limit(5).all()
        
        files_data = []
        for file in latest_files:
            file_pages = ReportPage.query.filter_by(file_id=file.file_id).count()
            files_data.append({
                'id': file.file_id,
                'name': file.file_name,
                'uploaded': file.upload_timestamp.isoformat() if file.upload_timestamp else 'Unknown',
                'pages': file_pages,
                'total_pages': file.total_pages
            })
        
        return jsonify({
            'status': 'connected',
            'timestamp': datetime.utcnow().isoformat(),
            'counts': {
                'files': files_count,
                'pages': pages_count
            },
            'latest_files': files_data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })



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
        print("=== UPLOAD ENDPOINT HIT ===")
        print("Request files:", request.files)
        print("Request form:", request.form)

        if 'file' not in request.files:
            print("No file in request")
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['file']
        print("File object:", file)
        print("File filename:", file.filename)

        if file.filename == '':
            print("Empty filename")
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        # Preliminary checks for AI components (keep these if you want)
        if classifier is None:
            print("Classifier not available")
            return jsonify({'success': False, 'error': 'YOLO classifier not available'}), 500
        if text_extractor is None:
            print("Text extractor not available")
            return jsonify({'success': False, 'error': 'Text extractor not available. Please check OpenAI API key configuration.'}), 500

        # Save uploaded file
        save_result = file_uploader.save_uploaded_file(file)
        print("Save result:", save_result)

        # Debug: ensure save succeeded before processing
        if not save_result.get('success'):
            print("Save failed:", save_result.get('error'))
            return jsonify({'success': False, 'error': save_result.get('error')}), 400

        # Insert a clear debug marker before processing
        print("DEBUG: Calling process_uploaded_file() for file_id:", save_result.get('file_id'))

        # Process the file (this is the call that was causing silent crashes)
        process_result = process_uploaded_file(save_result)

        print("DEBUG: process_uploaded_file returned:", process_result)

        return jsonify(process_result)

    except Exception as e:
        import traceback
        print("=== UPLOAD ENDPOINT EXCEPTION ===")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


def process_uploaded_file(file_info):
    """
    Process uploaded file through classification and extraction pipeline with batching
    """
    import traceback

    print("=== PROCESS START ===")
    print("file_info:", file_info)

    file_id = file_info['file_id']
    file_path = file_info['file_path']
    file_type = file_info['file_type']

    try:
        print("STEP A: Creating UploadedFile record")

        # Create file record in database
        file_record = UploadedFile(
            file_id=file_id,
            file_name=file_info['original_filename'],
            file_type=file_type,
            file_path=file_path
        )
        db.session.add(file_record)

        print("STEP B: Converting file to images")

        # Convert file to images
        images_dir = os.path.join(app.config['UPLOAD_FOLDER'], file_id)
        image_paths = []

        print(f"DEBUG: images_dir = {images_dir}")

        if file_type.lower() == 'pdf':
            print("DEBUG: file is PDF → converting using pdf2image")
            print(f"Converting PDF: {file_path}")
            image_paths = file_uploader.convert_pdf_to_images(file_path, images_dir)
            print(f"PDF conversion result: {len(image_paths)} images created")
        else:
            print("DEBUG: file is IMAGE → processing single image")
            image_paths = file_uploader.process_single_image(file_path, images_dir)
            print(f"Image processing result: {len(image_paths)} images created")

        if not image_paths:
            print("ERROR: image_paths is EMPTY — image conversion failed")
            raise Exception("Failed to convert file to images")

        print("STEP C: Starting classification loop")

        # Process each page - FIRST PASS: classification
        pages_data = []
        pages_with_remarks = 0

        for i, image_path in enumerate(image_paths):
            print(f"DEBUG: Classifying page {i+1} - {image_path}")

            page_id = str(uuid.uuid4())

            classification_result = classifier.classify_image(image_path)

            has_remarks = classification_result['has_remarks']
            confidence = classification_result['confidence']
            bounding_boxes = classification_result['bounding_boxes']

            if has_remarks:
                pages_with_remarks += 1

            pages_data.append({
                'page_id': page_id,
                'page_number': i + 1,
                'image_path': image_path,
                'has_remarks': has_remarks,
                'confidence': confidence,
                'bounding_boxes': bounding_boxes,
                'extracted_text': "",
                'original_text': "",
                'extraction_confidence': 0.0,
                'correction_applied': False
            })

        print("STEP D: Batch OCR for pages with remarks")

        # SECOND PASS: Batch text extraction
        if pages_with_remarks > 0:
            print(f"DEBUG: {pages_with_remarks} pages have remarks")

            remark_images = []
            remark_page_indices = []

            for i, p in enumerate(pages_data):
                if p['has_remarks']:
                    print(f"DEBUG: Extracting remark region for page {p['page_number']}")
                    remarks_image = classifier.extract_remarks_region(p['image_path'], p['bounding_boxes'])
                    if remarks_image:
                        remark_images.append(remarks_image)
                        remark_page_indices.append(i)

            if remark_images:
                print("DEBUG: Running batch_extract_text_from_images()")
                batch_result = text_extractor.batch_extract_text_from_images(remark_images)
                print("DEBUG: OCR batch_result received:", batch_result)

                # SAFE ASSIGNMENT BLOCK
                for idx, page_index in enumerate(remark_page_indices):

                    texts = batch_result.get("texts", [])
                    original_texts = batch_result.get("original_texts", [])
                    confidences = batch_result.get("confidences", [])
                    corrections = batch_result.get("correction_applied", [])

                    pages_data[page_index]['extracted_text'] = texts[idx] if idx < len(texts) else ""
                    pages_data[page_index]['original_text'] = original_texts[idx] if idx < len(original_texts) else ""
                    pages_data[page_index]['extraction_confidence'] = confidences[idx] if idx < len(confidences) else 0.0
                    pages_data[page_index]['correction_applied'] = corrections[idx] if idx < len(corrections) else False

        print("STEP E: Creating ReportPage DB entries")

        # Create database records
        pages_without_remarks = len(image_paths) - pages_with_remarks

        for page_data in pages_data:
            print(f"DEBUG: Storing ReportPage for page {page_data['page_number']}")

            page_record = ReportPage(
                page_id=page_data['page_id'],
                file_id=file_id,
                page_number=page_data['page_number'],
                has_remarks=page_data['has_remarks'],
                extracted_text=page_data['extracted_text'],
                original_text=page_data['original_text'],
                correction_applied=page_data['correction_applied'],
                improvement_score=page_data.get('improvement_score', 0.0),
                confidence_score=page_data['extraction_confidence'] if page_data['has_remarks'] else page_data['confidence'],
                image_path=page_data['image_path'],
                bounding_boxes=json.dumps(page_data['bounding_boxes'])
            )
            db.session.add(page_record)

        print("STEP F: Calculating criticality")

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

        file_record.total_pages = total_pages
        file_record.pages_with_remarks = pages_with_remarks
        file_record.pages_without_remarks = pages_without_remarks
        file_record.criticality_level = criticality

        print("STEP G: Committing to DB")

        db.session.commit()
        print("STEP G: Commit successful")

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
        print("=== FULL ERROR TRACEBACK ===")
        print(traceback.format_exc())
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
