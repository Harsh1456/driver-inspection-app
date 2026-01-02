import openai
import base64
from io import BytesIO
from PIL import Image
import time
import hashlib
import pickle
import os

class TextExtractor:
    """ChatGPT API-based text extractor for handwritten remarks with batch processing and correction"""
    
    def __init__(self, api_key, cache_dir="./extraction_cache"):
        """
        Initialize OpenAI client
        """
        self.api_key = api_key
        self.client = None
        self.cache_dir = cache_dir
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        if api_key and not api_key.startswith('your-openai-api-key'):
            try:
                self.client = openai.OpenAI(api_key=api_key)
            except Exception:
                self.client = None
    
    def extract_text_from_image(self, image, use_cache=True):
        """
        Extract handwritten text from image using ChatGPT API with caching and correction
        """
        if use_cache:
            image_hash = self._get_image_hash(image)
            cached_result = self._get_cached_result(image_hash)
            if cached_result:
                return cached_result
        
        # Original extraction logic
        result = self._actual_extract_text_from_image(image)
        
        # Apply correction to extracted text if extraction was successful
        if result['success'] and result['text'] != "NO_HANDWRITING_DETECTED":
            corrected_result = self.correct_extracted_text(result['text'])
            if corrected_result['success']:
                result['corrected_text'] = corrected_result['corrected_text']
                result['correction_applied'] = True
                result['improvement_score'] = corrected_result['improvement_score']
            else:
                result['correction_applied'] = False
                result['improvement_score'] = 0.0
        else:
            result['correction_applied'] = False
            result['improvement_score'] = 0.0
        
        if use_cache and result['success']:
            self._save_cached_result(image_hash, result)
        
        return result
    
    def correct_extracted_text(self, extracted_text):
        """
        Correct and improve extracted text using domain knowledge about vehicle inspection reports
        """
        try:
            if not self.client:
                return {
                    'success': False,
                    'corrected_text': extracted_text,
                    'error': 'OpenAI API client not configured'
                }
            
            # Enhanced correction prompt with comprehensive domain knowledge
            correction_prompt = """
            You are a Vehicle Inspection Report Specialist with deep expertise in truck and bus inspection terminology, abbreviations, and common handwriting patterns.

            TASK: Correct, clarify, and format the extracted handwritten text from a Driver's Vehicle Inspection Report.

            DOMAIN KNOWLEDGE BASE:
            COMMON VEHICLE SYSTEMS:
            - Braking: air brakes, hydraulic brakes, parking brake, brake pads, rotors, drums
            - Tires: tread depth, inflation, wear patterns, sidewall damage
            - Lighting: headlights, taillights, turn signals, brake lights, markers
            - Steering & Suspension: wheel alignment, shocks, struts, ball joints, tie rods
            - Engine: oil leaks, coolant, belts, hoses, filters, exhaust system
            - Transmission: gear shifting, clutch, fluid leaks
            - Electrical: battery, alternator, wiring, fuses
            - Safety: mirrors, windshield, wipers, horns, emergency equipment

            COMMON ABBREVIATIONS & CORRECTIONS:
            - "brks" → "brakes", "brk" → "brake"
            - "tirs" → "tires", "tre" → "tire"
            - "lites" → "lights", "lts" → "lights"
            - "stg" → "steering", "sus" → "suspension"
            - "eng" → "engine", "trans" → "transmission"
            - "elec" → "electrical", "bat" → "battery"
            - "mir" → "mirror", "ws" → "windshield"
            - "press" → "pressure", "PSI" → "PSI" (keep as is)
            - "mi" → "miles", "km" → "kilometers"
            - "L" or "LF" → "left front", "R" or "RF" → "right front"
            - "LR" → "left rear", "RR" → "right rear"

            COMMON CONDITION DESCRIPTORS:
            - "wrn" → "worn", "dam" → "damaged", "lk" → "leak", "leakg" → "leaking"
            - "crak" → "cracked", "mis" → "missing", "loos" → "loose"
            - "noizy" → "noisy", "brokn" → "broken", "faulty" → "faulty"
            - "low" → "low", "high" → "high", "unevn" → "uneven"

            CORRECTION RULES:
            1. CORRECT OBVIOUS SPELLING ERRORS: Fix common misspellings of vehicle parts and conditions
            2. EXPAND ABBREVIATIONS: Convert common abbreviations to full words, except standard units (PSI, RPM, MPG)
            3. MAINTAIN TECHNICAL TERMS: Keep proper technical names and part numbers intact
            4. PRESERVE MEASUREMENTS: Don't change numbers, pressures, or measurements
            5. IMPROVE READABILITY: Format as clear, complete sentences when possible
            6. MAINTAIN ORIGINAL MEANING: Never change the actual issue being reported
            7. KEEP UNCERTAINTY MARKERS: Preserve [illegible] and [??] markers for unclear text
            8. ADD CONTEXT: If handwriting suggests a common inspection item, make it explicit

            FORMATTING GUIDELINES:
            - Use bullet points for multiple items
            - Start with the most critical issues first
            - Use proper capitalization and punctuation
            - Group related issues together

            INPUT TEXT TO CORRECT:
            {extracted_text}

            CORRECTED OUTPUT (return only the corrected text, no explanations):
            """
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a Vehicle Inspection Report Specialist expert in correcting and clarifying handwritten inspection remarks."
                },
                {
                    "role": "user",
                    "content": correction_prompt.format(extracted_text=extracted_text)
                }
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=500,
                temperature=0.1
            )
            
            corrected_text = response.choices[0].message.content.strip()
            
            # Validate that correction actually improved the text
            if self.is_improvement(extracted_text, corrected_text):
                return {
                    'success': True,
                    'corrected_text': corrected_text,
                    'improvement_score': self.calculate_improvement_score(extracted_text, corrected_text)
                }
            else:
                return {
                    'success': False,
                    'corrected_text': extracted_text,
                    'error': 'Correction did not improve text quality'
                }
                
        except Exception as e:
            return {
                'success': False,
                'corrected_text': extracted_text,
                'error': f'Text correction failed: {str(e)}'
            }
    
    def is_improvement(self, original_text, corrected_text):
        """
        Check if the corrected text is actually an improvement
        """
        # If correction failed or returned empty, it's not an improvement
        if not corrected_text or corrected_text.strip() == "":
            return False
        
        # If correction is identical to original, it's not an improvement
        if original_text.strip() == corrected_text.strip():
            return False
        
        # Count meaningful improvements
        original_words = len(original_text.split())
        corrected_words = len(corrected_text.split())
        
        # Check for common improvement indicators
        improvement_indicators = [
            len(corrected_text) > len(original_text) * 0.8,  # Not significantly shorter
            corrected_words >= original_words * 0.7,  # Not losing too much content
            any(char.isupper() for char in corrected_text),  # Has proper capitalization
            any(char in corrected_text for char in ['.', '!', '?']),  # Has punctuation
        ]
        
        return sum(improvement_indicators) >= 3
    
    def calculate_improvement_score(self, original_text, corrected_text):
        """
        Calculate how much the correction improved the text (0.0 to 1.0)
        """
        score_factors = []
        
        # Length preservation factor
        original_len = len(original_text)
        corrected_len = len(corrected_text)
        if original_len > 0:
            length_ratio = min(corrected_len / original_len, 2.0)
            score_factors.append(min(length_ratio, 1.0) * 0.2)
        
        # Word count preservation factor
        original_words = len(original_text.split())
        corrected_words = len(corrected_text.split())
        if original_words > 0:
            word_ratio = min(corrected_words / original_words, 2.0)
            score_factors.append(min(word_ratio, 1.0) * 0.2)
        
        # Readability factor (based on punctuation and capitalization)
        sentence_endings = corrected_text.count('.') + corrected_text.count('!') + corrected_text.count('?')
        capital_letters = sum(1 for char in corrected_text if char.isupper())
        
        if corrected_words > 0:
            readability_score = min(
                (sentence_endings / max(corrected_words / 10, 1)) + 
                (capital_letters / max(corrected_words / 5, 1)), 
                1.0
            )
            score_factors.append(readability_score * 0.3)
        
        # Domain terminology factor
        domain_terms = [
            'brake', 'tire', 'light', 'steering', 'suspension', 'engine', 
            'transmission', 'electrical', 'mirror', 'windshield', 'pressure',
            'worn', 'damaged', 'leaking', 'cracked', 'missing', 'loose'
        ]
        domain_term_count = sum(1 for term in domain_terms if term in corrected_text.lower())
        domain_score = min(domain_term_count / 5, 1.0)
        score_factors.append(domain_score * 0.3)
        
        return min(sum(score_factors), 1.0)

    def batch_extract_text_from_images(self, images, max_batch_size=10):
        """
        Batch extract text from multiple images in a single API call to reduce cost and time
        """
        try:
            if not self.client:
                return {
                    'success': False,
                    'texts': [],
                    'confidences': [],
                    'error': 'OpenAI API client not configured'
                }
            
            # Split into smaller batches to avoid token limits
            batches = [images[i:i + max_batch_size] for i in range(0, len(images), max_batch_size)]
            all_texts = []
            all_confidences = []
            
            for batch_idx, image_batch in enumerate(batches):
                # Extract text first using batch extraction
                batch_result = self._batch_extract_only(image_batch)
                
                if batch_result['success']:
                    # Apply correction to each extracted text
                    corrected_texts = []
                    
                    for extracted_text in batch_result['texts']:
                        if extracted_text != "NO_HANDWRITING_DETECTED":
                            correction_result = self.correct_extracted_text(extracted_text)
                            if correction_result['success']:
                                corrected_texts.append(correction_result['corrected_text'])
                            else:
                                corrected_texts.append(extracted_text)
                        else:
                            corrected_texts.append(extracted_text)
                    
                    all_texts.extend(corrected_texts)
                    all_confidences.extend(batch_result['confidences'])
                else:
                    # Fallback: process individually
                    for image in image_batch:
                        individual_result = self.extract_text_from_image(image)
                        # Use corrected text if available, otherwise use original text
                        final_text = individual_result.get('corrected_text', individual_result.get('text', ''))
                        all_texts.append(final_text)
                        all_confidences.append(individual_result.get('confidence', 0.0))
            
            return {
                'success': True,
                'texts': all_texts,
                'confidences': all_confidences,
                'error': None
            }
            
        except Exception as e:
            error_msg = f"Batch extraction failed: {str(e)}"
            return {
                'success': False,
                'texts': [],
                'confidences': [],
                'error': error_msg
            }

    def _batch_extract_only(self, images):
        """
        Batch extraction without correction (internal method)
        """
        # Prepare messages for batch processing
        messages = [{
            "role": "user",
            "content": []
        }]
        
        # Add system prompt for raw extraction (without correction)
        system_prompt = {
            "type": "text",
            "text": """
            You are analyzing multiple handwritten remarks sections from Driver's Vehicle Inspection Reports.
            
            CRITICAL: You will receive multiple images. Process them in the EXACT ORDER they are provided.
            The first image is IMAGE 1, the second is IMAGE 2, and so on.
            
            For EACH image, extract ONLY the handwritten text exactly as written and maintain this exact format:
            
            IMAGE 1: [raw extracted text for first image]
            IMAGE 2: [raw extracted text for second image] 
            IMAGE 3: [raw extracted text for third image]
            
            IMPORTANT RULES FOR RAW EXTRACTION:
            1. Extract text exactly as written - DO NOT correct spelling or grammar
            2. Preserve all abbreviations, misspellings, and variations
            3. Maintain the original line breaks and spacing
            4. Ignore pre-printed text, lines, boxes
            5. If no handwritten text is visible, use "NO_HANDWRITING_DETECTED"
            6. Do NOT skip any images - provide output for every image in order
            7. Do NOT combine text from multiple images
            
            Return ONLY in the format shown above with no additional text.
            """
        }
        messages[0]["content"].append(system_prompt)
        
        # Add all images to the message
        for i, image in enumerate(images):
            # Convert image to base64
            buffered = BytesIO()
            enhanced_image = self.enhance_image_for_ocr(image)
            enhanced_image.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            image_content = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_base64}",
                    "detail": "high"
                }
            }
            messages[0]["content"].append(image_content)
            
            # Add separator text between images
            if i < len(images) - 1:
                separator = {
                    "type": "text",
                    "text": f"\n--- PROCESS IMAGE {i+1} ABOVE THEN CONTINUE ---\n"
                }
                messages[0]["content"].append(separator)
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=400 * len(images),
                temperature=0.1
            )
            
            batch_text = response.choices[0].message.content.strip()
            
            # Parse the response to extract individual image texts
            batch_texts = self._parse_batch_response(batch_text, len(images))
            
            # Calculate confidence for each extracted text
            batch_confidences = [self.calculate_confidence(text) for text in batch_texts]
            
            return {
                'success': True,
                'texts': batch_texts,
                'confidences': batch_confidences
            }
            
        except Exception as e:
            return {
                'success': False,
                'texts': [],
                'confidences': [],
                'error': str(e)
            }

    def _parse_batch_response(self, batch_text, expected_count):
        """
        Parse batch API response to extract individual image texts with strict order matching
        """
        # Initialize with defaults
        texts = ["NO_HANDWRITING_DETECTED"] * expected_count
        
        # Clean the batch text first
        batch_text = batch_text.strip()
        
        # Look for explicit image markers first
        for i in range(expected_count):
            # Try multiple possible formats
            markers = [
                f"IMAGE {i+1}:",
                f"IMAGE_{i+1}:", 
                f"IMAGE{i+1}:",
                f"PAGE {i+1}:",
                f"PAGE_{i+1}:",
                f"{i+1}:",
                f"{i+1}."
            ]
            
            for marker in markers:
                if marker in batch_text:
                    # Extract text after this marker until next marker or end
                    start_idx = batch_text.find(marker) + len(marker)
                    end_idx = len(batch_text)
                    
                    # Look for the next marker
                    for next_i in range(i+2, expected_count+2):
                        next_markers = [
                            f"IMAGE {next_i}:",
                            f"IMAGE_{next_i}:",
                            f"PAGE {next_i}:",
                            f"{next_i}:"
                        ]
                        for next_marker in next_markers:
                            if next_marker in batch_text[start_idx:]:
                                next_idx = batch_text.find(next_marker, start_idx)
                                if next_idx > start_idx:
                                    end_idx = next_idx
                                    break
                        if end_idx != len(batch_text):
                            break
                    
                    # Extract and clean the text
                    extracted = batch_text[start_idx:end_idx].strip()
                    
                    # Remove any trailing markers or separators
                    lines = extracted.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        line = line.strip()
                        # Skip lines that are separators or empty
                        if (not line or 
                            any(sep in line for sep in ['---', '###', '===']) or
                            any(m in line.upper() for m in ['IMAGE', 'PAGE', 'RESULT'])):
                            continue
                        cleaned_lines.append(line)
                    
                    if cleaned_lines:
                        texts[i] = '\n'.join(cleaned_lines)
                    break
        
        # Fallback: If no markers found, try to split by common patterns
        if all(text == "NO_HANDWRITING_DETECTED" for text in texts):
            # Try splitting by double newlines
            if '\n\n' in batch_text:
                parts = [part.strip() for part in batch_text.split('\n\n') if part.strip()]
                for i in range(min(expected_count, len(parts))):
                    # Clean each part
                    lines = parts[i].split('\n')
                    cleaned_lines = []
                    for line in lines:
                        line = line.strip()
                        if (not line or 
                            any(sep in line for sep in ['---', '###', '===']) or
                            any(m in line.upper() for m in ['IMAGE', 'PAGE', 'RESULT'])):
                            continue
                        cleaned_lines.append(line)
                    if cleaned_lines:
                        texts[i] = '\n'.join(cleaned_lines)
        
        # Final validation: Check if extracted text is actually meaningful
        for i in range(len(texts)):
            if texts[i] != "NO_HANDWRITING_DETECTED":
                if not self.is_valid_extraction(texts[i]):
                    texts[i] = "NO_HANDWRITING_DETECTED"
        
        return texts
    
    def _get_image_hash(self, image):
        """Generate hash for image to use as cache key"""
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        image_data = buffered.getvalue()
        return hashlib.md5(image_data).hexdigest()
    
    def _get_cached_result(self, image_hash):
        """Get cached extraction result"""
        cache_path = os.path.join(self.cache_dir, f"{image_hash}.pkl")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
        return None
    
    def _save_cached_result(self, image_hash, result):
        """Save extraction result to cache"""
        cache_path = os.path.join(self.cache_dir, f"{image_hash}.pkl")
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(result, f)
        except:
            pass
    
    def enhance_image_for_ocr(self, image):
        """
        Enhance image for better OCR performance
        """
        try:
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if image is too small
            min_size = 300
            width, height = image.size
            if min(width, height) < min_size:
                scale_factor = min_size / min(width, height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            return image
            
        except Exception:
            return image
    
    def is_valid_extraction(self, text):
        """
        Validate if the extracted text is meaningful
        """
        if not text or text == "NO_HANDWRITING_DETECTED":
            return False
        
        # Remove common false positives and check if meaningful content remains
        cleaned_text = text.strip()
        
        # Check for common false positive patterns
        false_positives = [
            "NO_HANDWRITING_DETECTED",
            "no handwriting detected", 
            "illegible",
            "[illegible]",
            "no text",
            "blank"
        ]
        
        if any(fp in cleaned_text.lower() for fp in false_positives):
            return False
        
        # Count meaningful characters (letters, numbers)
        meaningful_chars = sum(1 for char in cleaned_text if char.isalnum())
        
        # Require at least 2 meaningful characters (could be just "OK", "yes", etc.)
        if meaningful_chars < 2:
            return False
        
        # Check if it's mostly symbols or whitespace
        symbol_count = sum(1 for char in cleaned_text if not char.isalnum() and not char.isspace())
        if symbol_count > meaningful_chars * 2:
            return False
        
        return True
    
    def calculate_confidence(self, text):
        """
        Calculate confidence score based on text characteristics
        """
        if not text or text == "NO_HANDWRITING_DETECTED":
            return 0.0
        
        confidence_factors = []
        
        # Length factor
        length_factor = min(len(text) / 50, 1.0)
        confidence_factors.append(length_factor * 0.3)
        
        # Word count factor
        words = text.split()
        word_factor = min(len(words) / 5, 1.0)
        confidence_factors.append(word_factor * 0.3)
        
        # Alphanumeric ratio factor
        if len(text) > 0:
            alpha_ratio = sum(1 for char in text if char.isalnum()) / len(text)
            confidence_factors.append(alpha_ratio * 0.4)
        else:
            confidence_factors.append(0.0)
        
        return min(sum(confidence_factors), 1.0)
    
    def extract_text_from_image_path(self, image_path):
        """
        Extract text from image file path
        """
        try:
            image = Image.open(image_path)
            return self.extract_text_from_image(image)
        except Exception as e:
            return {
                'success': False,
                'text': '',
                'confidence': 0.0,
                'error': str(e)
            }

    def _actual_extract_text_from_image(self, image):
        """
        The actual extraction logic (raw extraction without correction)
        """
        try:
            if not self.client:
                return {
                    'success': False,
                    'text': '',
                    'confidence': 0.0,
                    'error': 'OpenAI API client not configured'
                }
            
            # Convert image to base64
            buffered = BytesIO()
            
            # Enhance image for better OCR
            enhanced_image = self.enhance_image_for_ocr(image)
            enhanced_image.save(buffered, format="JPEG", quality=95)
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Updated prompt for RAW extraction (no correction)
            raw_extraction_prompt = """
            You are analyzing a handwritten remarks section from a Driver's Vehicle Inspection Report. 

            CRITICAL INSTRUCTIONS - RAW EXTRACTION ONLY:
            1. Extract ALL handwritten text EXACTLY as written - DO NOT correct spelling or grammar
            2. Preserve ALL abbreviations, misspellings, and variations exactly as they appear
            3. Focus on the handwritten text only - ignore any pre-printed text, lines, boxes, or form elements
            4. If text is partially legible, provide your best interpretation WITHOUT correction
            5. Maintain the original line breaks and spacing as much as possible
            6. If multiple handwriting styles exist, capture all of them exactly as written
            7. Include numbers, symbols, and special characters exactly as they appear

            DOMAIN CONTEXT (for interpretation only, NOT for correction):
            - This is from truck/bus inspection reports
            - Common vehicle parts: brakes, tires, lights, steering, suspension, engine, transmission, exhaust
            - Common conditions: worn, damaged, leaking, cracked, missing, loose, noisy
            - Common abbreviations may be used

            TEXT EXTRACTION GUIDELINES:
            - DO NOT correct any spelling errors
            - DO NOT expand abbreviations
            - DO NOT improve grammar or formatting
            - If uncertain about a word, include it as-is but add [??] after it
            - For completely illegible words, use [illegible]
            - Preserve the raw, original text exactly as written

            OUTPUT FORMAT:
            Return ONLY the raw extracted text without any additional commentary or headers.
            Format multiple lines naturally as they appear.
            If no handwritten text is visible, return "NO_HANDWRITING_DETECTED".
            """
            
            # Prepare messages for ChatGPT
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": raw_extraction_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            # Use gpt-4o model
            model_name = "gpt-4o"
            
            # Call OpenAI API with retry logic
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        max_tokens=500,
                        temperature=0.1
                    )
                    
                    extracted_text = response.choices[0].message.content.strip()
                    
                    # Validate extraction
                    if self.is_valid_extraction(extracted_text):
                        confidence = self.calculate_confidence(extracted_text)
                        return {
                            'success': True,
                            'text': extracted_text,
                            'confidence': confidence,
                            'error': None
                        }
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(1)
                            continue
                        else:
                            return {
                                'success': False,
                                'text': '',
                                'confidence': 0.0,
                                'error': 'Extraction validation failed'
                            }
                            
                except openai.BadRequestError as e:
                    error_msg = f"Model {model_name} doesn't support vision or is unavailable: {str(e)}"
                    return {
                        'success': False,
                        'text': '',
                        'confidence': 0.0,
                        'error': error_msg
                    }
                except openai.RateLimitError:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        time.sleep(wait_time)
                        continue
                    else:
                        raise
                except openai.AuthenticationError as e:
                    error_msg = f'OpenAI API authentication failed: {str(e)}'
                    return {
                        'success': False,
                        'text': '',
                        'confidence': 0.0,
                        'error': error_msg
                    }
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    else:
                        raise
            
        except Exception as e:
            error_msg = f"Text extraction failed: {str(e)}"
            return {
                'success': False,
                'text': '',
                'confidence': 0.0,
                'error': error_msg
            }