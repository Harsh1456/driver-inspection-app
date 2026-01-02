from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class UploadedFile(db.Model):
    """Model for storing uploaded file metadata"""
    
    __tablename__ = 'uploaded_files'
    
    file_id = db.Column(db.String(36), primary_key=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    total_pages = db.Column(db.Integer, default=0)
    pages_with_remarks = db.Column(db.Integer, default=0)
    pages_without_remarks = db.Column(db.Integer, default=0)
    criticality_level = db.Column(db.String(20), default='GREEN')
    file_path = db.Column(db.String(500))
    
    # Relationship with report pages
    pages = db.relationship('ReportPage', backref='file', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'file_id': self.file_id,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'upload_timestamp': self.upload_timestamp.isoformat(),
            'total_pages': self.total_pages,
            'pages_with_remarks': self.pages_with_remarks,
            'pages_without_remarks': self.pages_without_remarks,
            'criticality_level': self.criticality_level,
            'file_path': self.file_path,
            'criticality_percentage': self.criticality_percentage
        }
    
    @property
    def criticality_percentage(self):
        """Calculate percentage of pages with remarks"""
        if self.total_pages == 0:
            return 0
        return round((self.pages_with_remarks / self.total_pages) * 100, 2)


class ReportPage(db.Model):
    """Model for storing individual page processing results"""
    
    __tablename__ = 'report_pages'
    
    page_id = db.Column(db.String(36), primary_key=True)
    file_id = db.Column(db.String(36), db.ForeignKey('uploaded_files.file_id'), nullable=False)
    page_number = db.Column(db.Integer, nullable=False)
    has_remarks = db.Column(db.Boolean, default=False)
    extracted_text = db.Column(db.Text)
    original_text = db.Column(db.Text)  # NEW: Store raw extracted text before correction
    correction_applied = db.Column(db.Boolean, default=False)  # NEW: Track if correction was applied
    improvement_score = db.Column(db.Float, default=0.0)  # NEW: Score for correction quality
    confidence_score = db.Column(db.Float)
    image_path = db.Column(db.String(500))
    processed_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    bounding_boxes = db.Column(db.Text)
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'page_id': self.page_id,
            'file_id': self.file_id,
            'page_number': self.page_number,
            'has_remarks': self.has_remarks,
            'extracted_text': self.extracted_text,
            'original_text': self.original_text,  # NEW: Include original text in response
            'correction_applied': self.correction_applied,  # NEW: Include correction status
            'improvement_score': self.improvement_score,  # NEW: Include improvement score
            'confidence_score': self.confidence_score,
            'image_path': self.image_path,
            'processed_timestamp': self.processed_timestamp.isoformat(),
            'bounding_boxes': json.loads(self.bounding_boxes) if self.bounding_boxes else []
        }
    
    @property
    def display_text(self):
        """Get the text to display (corrected if available, otherwise original)"""
        return self.extracted_text if self.extracted_text else self.original_text
    
    @property
    def has_correction(self):
        """Check if this page has corrected text"""
        return self.correction_applied and self.extracted_text and self.original_text