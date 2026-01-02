from flask import Blueprint, render_template, request, jsonify, send_file
from database import db, UploadedFile, ReportPage
import os
import json
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@dashboard_bp.route('/dashboard')
def dashboard():
    """Main dashboard showing all uploaded files"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '')
    
    # Build query
    query = UploadedFile.query
    
    if search:
        query = query.filter(UploadedFile.file_name.ilike(f'%{search}%'))
    
    # Get paginated results
    files = query.order_by(UploadedFile.upload_timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('dashboard.html', files=files, search=search)

@dashboard_bp.route('/api/files')
def get_files_api():
    """API endpoint to get uploaded files data"""
    files = UploadedFile.query.order_by(UploadedFile.upload_timestamp.desc()).all()
    
    files_data = []
    for file in files:
        file_data = file.to_dict()
        files_data.append(file_data)
    
    return jsonify({
        'success': True,
        'files': files_data,
        'total': len(files_data)
    })

@dashboard_bp.route('/file/<file_id>')
def file_detail(file_id):
    """Detailed view of a specific file"""
    file = UploadedFile.query.get_or_404(file_id)
    pages = ReportPage.query.filter_by(file_id=file_id).order_by(ReportPage.page_number).all()
    
    return render_template('file_detail.html', file=file, pages=pages)

@dashboard_bp.route('/api/file/<file_id>')
def file_detail_api(file_id):
    """API endpoint for file details"""
    file = UploadedFile.query.get_or_404(file_id)
    pages = ReportPage.query.filter_by(file_id=file_id).order_by(ReportPage.page_number).all()
    
    file_data = file.to_dict()
    pages_data = [page.to_dict() for page in pages]
    
    return jsonify({
        'success': True,
        'file': file_data,
        'pages': pages_data
    })

@dashboard_bp.route('/api/file/<file_id>/delete', methods=['DELETE'])
def delete_file(file_id):
    """Delete a file and all its pages"""
    try:
        file = UploadedFile.query.get_or_404(file_id)
        
        # Delete associated pages
        ReportPage.query.filter_by(file_id=file_id).delete()
        
        # Delete the file record
        db.session.delete(file)
        db.session.commit()
        
        # TODO: Delete actual files from disk (optional)
        
        return jsonify({
            'success': True,
            'message': 'File deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting file: {str(e)}'
        }), 500

@dashboard_bp.route('/api/page/<page_id>/update-text', methods=['POST'])
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

@dashboard_bp.route('/api/stats')
def get_stats():
    """Get dashboard statistics"""
    total_files = UploadedFile.query.count()
    total_pages = db.session.query(ReportPage).count()
    pages_with_remarks = ReportPage.query.filter_by(has_remarks=True).count()
    
    # Criticality distribution
    criticality_counts = {
        'GREEN': UploadedFile.query.filter_by(criticality_level='GREEN').count(),
        'ORANGE': UploadedFile.query.filter_by(criticality_level='ORANGE').count(),
        'RED': UploadedFile.query.filter_by(criticality_level='RED').count()
    }
    
    return jsonify({
        'success': True,
        'stats': {
            'total_files': total_files,
            'total_pages': total_pages,
            'pages_with_remarks': pages_with_remarks,
            'criticality_distribution': criticality_counts
        }
    })