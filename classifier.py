import cv2
import numpy as np
from ultralytics import YOLO
import os
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class RemarkClassifier:
    """YOLOv8-based classifier for detecting handwritten remarks"""
    
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.class_names = ['No Remarks', 'Remarks']
        self.load_model()
    
    def load_model(self):
        """Load the YOLOv8 model"""
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"YOLO model not found at {self.model_path}")
            
            self.model = YOLO(self.model_path)
            logger.info("YOLO model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading YOLO model: {str(e)}")
            raise
    
    def classify_image(self, image_path, confidence_threshold=0.5):
        """
        Classify if an image has handwritten remarks
        """
        try:
            if not os.path.exists(image_path):
                raise ValueError(f"Image file not found: {image_path}")
                
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image from {image_path}")
            
            # Run YOLO inference
            results = self.model(image, conf=confidence_threshold, verbose=False)
            
            has_remarks = False
            confidence = 0.0
            bounding_boxes = []
            
            if len(results[0].boxes) > 0:
                boxes = results[0].boxes
                confidences = boxes.conf.cpu().numpy()
                class_ids = boxes.cls.cpu().numpy()
                
                # Look for "Remarks" class (class 1)
                remarks_indices = np.where(class_ids == 1)[0]
                
                if len(remarks_indices) > 0:
                    has_remarks = True
                    remarks_confidences = confidences[remarks_indices]
                    confidence = float(np.max(remarks_confidences)) if len(remarks_confidences) > 0 else 0.0
                    
                    remarks_boxes = boxes.xyxy[remarks_indices].cpu().numpy()
                    for box in remarks_boxes:
                        bounding_boxes.append({
                            'x1': float(box[0]),
                            'y1': float(box[1]),
                            'x2': float(box[2]),
                            'y2': float(box[3]),
                            'confidence': float(confidences[remarks_indices[0]])
                        })
            
            return {
                'has_remarks': has_remarks,
                'confidence': confidence,
                'bounding_boxes': bounding_boxes,
                'total_detections': len(results[0].boxes),
                'class_distribution': self._get_class_distribution(results[0])
            }
            
        except Exception as e:
            logger.error(f"Error classifying image {image_path}: {str(e)}")
            return {
                'has_remarks': False,
                'confidence': 0.0,
                'bounding_boxes': [],
                'total_detections': 0,
                'error': str(e)
            }
    
    def _get_class_distribution(self, result):
        """Get distribution of detected classes"""
        if len(result.boxes) == 0:
            return {}
        
        class_ids = result.boxes.cls.cpu().numpy()
        unique, counts = np.unique(class_ids, return_counts=True)
        
        distribution = {}
        for class_id, count in zip(unique, counts):
            class_name = self.model.names[int(class_id)] if hasattr(self.model, 'names') else f"Class_{int(class_id)}"
            distribution[class_name] = int(count)
        
        return distribution
    
    def extract_remarks_region(self, image_path, bounding_boxes):
        """
        Extract the remarks region from image based on bounding boxes
        """
        try:
            if not bounding_boxes:
                # print("No bounding boxes provided for remarks extraction")
                return None
            
            image = cv2.imread(image_path)
            if image is None:
                # print(f"Could not load image from {image_path}")
                return None
            
            # Use the bounding box with highest confidence
            best_box = max(bounding_boxes, key=lambda x: x.get('confidence', 0))
            x1, y1, x2, y2 = int(best_box['x1']), int(best_box['y1']), int(best_box['x2']), int(best_box['y2'])
            
            # print(f"Extracting remarks region at coordinates: ({x1}, {y1}) to ({x2}, {y2})")
            
            # Add padding (reduced padding for better accuracy)
            padding = 10
            h, w = image.shape[:2]
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(w, x2 + padding)
            y2 = min(h, y2 + padding)
            
            if x2 <= x1 or y2 <= y1:
                # print(f"Invalid coordinates after padding: ({x1}, {y1}) to ({x2}, {y2})")
                return None
            
            remarks_region = image[y1:y2, x1:x2]
            
            if remarks_region.size == 0:
                # print("Extracted remarks region is empty")
                return None
            
            # print(f"Successfully extracted remarks region with size: {remarks_region.shape}")
            
            # Convert to PIL Image
            remarks_pil = Image.fromarray(cv2.cvtColor(remarks_region, cv2.COLOR_BGR2RGB))
            
            return remarks_pil
            
        except Exception as e:
            # print(f"Error extracting remarks region: {str(e)}")
            return None
