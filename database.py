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
    # Relationship with vehicle inspections
    inspection = db.relationship('VehicleInspection', backref='file', uselist=False, lazy=True, cascade='all, delete-orphan')
    # Relationship with edits
    edits = db.relationship('InspectionEdit', backref='file', lazy=True, cascade='all, delete-orphan')
    
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
    original_text = db.Column(db.Text)  # Store raw extracted text before correction
    correction_applied = db.Column(db.Boolean, default=False)  # Track if correction was applied
    improvement_score = db.Column(db.Float, default=0.0)  # Score for correction quality
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
            'original_text': self.original_text,  # Include original text in response
            'correction_applied': self.correction_applied,  # Include correction status
            'improvement_score': self.improvement_score,  # Include improvement score
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


class VehicleInspection(db.Model):
    """Model for storing extracted vehicle inspection data"""
    
    __tablename__ = 'vehicle_inspections'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(36), db.ForeignKey('uploaded_files.file_id'), nullable=False, unique=True)
    carrier_name = db.Column(db.String(255))
    location = db.Column(db.String(255))
    inspection_date = db.Column(db.String(50))  # Storing as string to handle various formats
    inspection_time = db.Column(db.String(50))
    truck_number = db.Column(db.String(50))
    odometer_reading = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'file_id': self.file_id,
            'carrier_name': self.carrier_name,
            'location': self.location,
            'inspection_date': self.inspection_date,
            'inspection_time': self.inspection_time,
            'truck_number': self.truck_number,
            'odometer_reading': self.odometer_reading,
            'created_at': self.created_at.isoformat()
        }


class InspectionEdit(db.Model):
    """Model for storing report edits and signatures with enhanced fields"""
    
    __tablename__ = 'inspection_edits'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(36), db.ForeignKey('uploaded_files.file_id'), nullable=False)
    signature_data = db.Column(db.Text)  # Base64 encoded signature image
    signature_type = db.Column(db.String(20))  # drawn, uploaded, typed
    signer_name = db.Column(db.String(255))
    signer_role = db.Column(db.String(200))  # Inspector's title/role
    signature_date = db.Column(db.String(50))  # Date of authorization
    edited_remarks = db.Column(db.Text)
    original_remarks = db.Column(db.Text)
    edited_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'file_id': self.file_id,
            'signature_type': self.signature_type,
            'signer_name': self.signer_name,
            'signer_role': self.signer_role,
            'signature_date': self.signature_date,
            'edited_remarks': self.edited_remarks,
            'original_remarks': self.original_remarks,
            'edited_at': self.edited_at.isoformat(),
            'has_signature': bool(self.signature_data),
            'signature_preview': self.get_signature_preview()
        }
    
    def get_signature_preview(self):
        """Generate a preview string for the signature"""
        if self.signer_name:
            if self.signer_role:
                return f"{self.signer_name} ({self.signer_role})"
            return self.signer_name
        return "No signature"
    
    @property
    def formatted_date(self):
        """Get formatted date for display"""
        if self.signature_date:
            return self.signature_date
        if self.edited_at:
            return self.edited_at.strftime('%Y-%m-%d')
        return "N/A"


# Create composite indexes for better query performance
db.Index('idx_file_pages', ReportPage.file_id, ReportPage.page_number)
db.Index('idx_upload_timestamp', UploadedFile.upload_timestamp)
db.Index('idx_edits_file', InspectionEdit.file_id, InspectionEdit.edited_at.desc())
db.Index('idx_inspection_file', VehicleInspection.file_id)
