# # """
# # OCR Processor - Enhanced with Date and Amount Extraction
# # """

# # import pytesseract
# # from PIL import Image
# # import cv2
# # import numpy as np
# # import re
# # from datetime import datetime
# # from typing import Dict, Optional, Tuple

# # class OCRProcessor:
# #     """Enhanced OCR with intelligent data extraction"""
    
# #     def __init__(self):
# #         self.tesseract_config = '--oem 3 --psm 6'
    
# #     def process_document(self, image: Image.Image, engine: str = 'tesseract') -> dict:
# #         """Process document with OCR"""
# #         try:
# #             import time
# #             start_time = time.time()
            
# #             # Convert PIL to CV2
# #             img_array = np.array(image)
            
# #             # Preprocess
# #             processed = self.preprocess_image(img_array)
            
# #             # OCR
# #             text = pytesseract.image_to_string(processed, config=self.tesseract_config)
            
# #             # Get confidence
# #             data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
# #             confidences = [int(conf) for conf in data['conf'] if conf != '-1']
# #             avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
# #             processing_time = time.time() - start_time
            
# #             return {
# #                 'success': True,
# #                 'text': text,
# #                 'confidence': avg_confidence,
# #                 'processing_time': processing_time
# #             }
        
# #         except Exception as e:
# #             return {
# #                 'success': False,
# #                 'error': str(e),
# #                 'text': '',
# #                 'confidence': 0,
# #                 'processing_time': 0
# #             }
    
# #     def preprocess_image(self, image: np.ndarray) -> np.ndarray:
# #         """Preprocess image for better OCR"""
# #         # Convert to grayscale
# #         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
# #         # Denoise
# #         denoised = cv2.fastNlMeansDenoising(gray)
        
# #         # Threshold
# #         _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
# #         return thresh
    
# #     def extract_bill_details(self, text: str) -> Dict:
# #         """
# #         Extract structured data from OCR text
# #         Returns: {amount, date, merchant, items}
# #         """
        
# #         return {
# #             'amount': self.extract_amount(text),
# #             'date': self.extract_date(text),
# #             'merchant': self.extract_merchant(text),
# #             'total_label': self.find_total_label(text)
# #         }
    
# #     def extract_amount(self, text: str) -> Optional[float]:
# #         """Extract monetary amount from text"""
        
# #         # Patterns for Indian currency
# #         patterns = [
# #             r'(?:total|amount|sum|grand total|net amount)[\s:]*₹?\s*(\d+(?:,\d+)?(?:\.\d{2})?)',
# #             r'₹\s*(\d+(?:,\d+)?(?:\.\d{2})?)',
# #             r'rs\.?\s*(\d+(?:,\d+)?(?:\.\d{2})?)',
# #             r'inr\s*(\d+(?:,\d+)?(?:\.\d{2})?)',
# #             r'(?:pay|paid|payment)[\s:]*₹?\s*(\d+(?:,\d+)?(?:\.\d{2})?)',
# #         ]
        
# #         amounts = []
        
# #         for pattern in patterns:
# #             matches = re.finditer(pattern, text, re.IGNORECASE)
# #             for match in matches:
# #                 amount_str = match.group(1).replace(',', '')
# #                 try:
# #                     amount = float(amount_str)
# #                     if 1 <= amount <= 1000000:  # Reasonable range
# #                         amounts.append(amount)
# #                 except:
# #                     continue
        
# #         # Return the largest amount found (likely the total)
# #         return max(amounts) if amounts else None
    
# #     def extract_date(self, text: str) -> Optional[str]:
# #         """Extract date from text"""
        
# #         # Date patterns
# #         patterns = [
# #             r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',  # DD-MM-YYYY or MM/DD/YYYY
# #             r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',    # YYYY-MM-DD
# #             r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})',  # DD Mon YYYY
# #             r'(?:date|bill date|invoice date)[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
# #         ]
        
# #         for pattern in patterns:
# #             match = re.search(pattern, text, re.IGNORECASE)
# #             if match:
# #                 date_str = match.group(1)
                
# #                 # Try to parse
# #                 parsed_date = self.parse_date_string(date_str)
# #                 if parsed_date:
# #                     return parsed_date
        
# #         return None
    
# #     def parse_date_string(self, date_str: str) -> Optional[str]:
# #         """Parse various date formats to ISO format"""
        
# #         formats = [
# #             '%d-%m-%Y', '%d/%m/%Y', '%d-%m-%y', '%d/%m/%y',
# #             '%Y-%m-%d', '%Y/%m/%d',
# #             '%d %b %Y', '%d %B %Y',
# #         ]
        
# #         for fmt in formats:
# #             try:
# #                 date_obj = datetime.strptime(date_str, fmt)
# #                 return date_obj.date().isoformat()
# #             except:
# #                 continue
        
# #         return None
    
# #     def extract_merchant(self, text: str) -> Optional[str]:
# #         """Extract merchant/store name from text"""
        
# #         # Usually at the top of the bill
# #         lines = text.split('\n')[:5]  # Check first 5 lines
        
# #         # Look for company-like names (capitalized words)
# #         for line in lines:
# #             line = line.strip()
# #             if len(line) > 3 and line[0].isupper():
# #                 # Check if it's likely a company name
# #                 if any(keyword in line.lower() for keyword in ['pvt', 'ltd', 'store', 'mart', 'shop', 'cafe', 'restaurant']):
# #                     return line
                
# #                 # If it's all caps and reasonable length
# #                 if line.isupper() and 3 < len(line) < 30:
# #                     return line
        
# #         return None
    
# #     def find_total_label(self, text: str) -> Optional[str]:
# #         """Find the line containing 'Total' or similar"""
        
# #         labels = ['total', 'grand total', 'net amount', 'amount payable', 'final amount']
        
# #         for line in text.split('\n'):
# #             line_lower = line.lower()
# #             for label in labels:
# #                 if label in line_lower:
# #                     return line.strip()
        
# #         return None

# """
# OCR Processor - Enhanced with Amount, Date, Merchant Extraction
# Production-Ready Version (Optimized + Stable)
# """

# import os
# import re
# import cv2
# import pytesseract
# import numpy as np
# from PIL import Image
# from datetime import datetime
# from typing import Dict, Optional, Any
# from core.config import settings


# # Make sure Tesseract path works on Windows/Linux/Mac
# if settings.TESSERACT_PATH and os.path.exists(settings.TESSERACT_PATH):
#     pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
# else:
#     # Safe fallback — allows Railway/macOS/Linux to auto-detect
#     pass


# class OCRProcessor:
#     """Enhanced OCR + Data Extraction"""

#     def __init__(self):
#         # OEM 3 (best accuracy), PSM 6 (block of text)
#         self.tesseract_config = "--oem 3 --psm 6"

#     # ------------------------------------------------------------
#     # MAIN OCR PROCESS
#     # ------------------------------------------------------------
#     def process_document(self, image: Image.Image) -> Dict[str, Any]:
#         """Run OCR and return text + confidence + processing time."""

#         try:
#             import time
#             start = time.time()

#             # Convert PIL → numpy array for OpenCV
#             img = np.array(image)

#             # Preprocess for better OCR
#             preprocessed = self.preprocess_image(img)

#             # Read text
#             text = pytesseract.image_to_string(
#                 preprocessed,
#                 config=self.tesseract_config,
#             )

#             # Collect confidence scores
#             data = pytesseract.image_to_data(
#                 preprocessed,
#                 output_type=pytesseract.Output.DICT,
#                 config=self.tesseract_config,
#             )

#             confidences = []
#             for conf in data.get("conf", []):
#                 try:
#                     c = float(conf)
#                     if c >= 0:
#                         confidences.append(c)
#                 except:
#                     pass

#             avg_conf = sum(confidences) / len(confidences) if confidences else 0
#             end = time.time()

#             return {
#                 "success": True,
#                 "text": text,
#                 "confidence": round(avg_conf, 2),
#                 "processing_time": round(end - start, 4),
#             }

#         except Exception as e:
#             return {
#                 "success": False,
#                 "error": str(e),
#                 "text": "",
#                 "confidence": 0.0,
#                 "processing_time": 0.0,
#             }

#     # ------------------------------------------------------------
#     # IMAGE PREPROCESSING
#     # ------------------------------------------------------------
#     def preprocess_image(self, img: np.ndarray) -> np.ndarray:
#         """Improve OCR accuracy using CV2 filters."""

#         # Convert to grayscale
#         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

#         # Denoise
#         denoised = cv2.fastNlMeansDenoising(gray, h=10)

#         # Otsu threshold for clean text
#         _, thresh = cv2.threshold(
#             denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
#         )

#         return thresh

#     # ------------------------------------------------------------
#     # STRUCTURED DATA EXTRACTION
#     # ------------------------------------------------------------
#     def extract_bill_details(self, text: str) -> Dict[str, Any]:
#         """Return structured bill data."""
#         return {
#             "amount": self.extract_amount(text),
#             "date": self.extract_date(text),
#             "merchant": self.extract_merchant(text),
#             "total_label": self.find_total_label(text),
#         }

#     # ---------------- AMOUNT EXTRACTION -----------------
#     def extract_amount(self, text: str) -> Optional[float]:
#         """Extract the most relevant (largest) monetary amount."""

#         patterns = [
#             r"(?:total|amount|net|grand total)[\s:₹]*([\d,]+(?:\.\d{1,2})?)",
#             r"₹\s*([\d,]+(?:\.\d{1,2})?)",
#             r"rs\.?\s*([\d,]+(?:\.\d{1,2})?)",
#             r"inr\s*([\d,]+(?:\.\d{1,2})?)",
#         ]

#         amounts = []

#         for p in patterns:
#             for match in re.finditer(p, text, re.IGNORECASE):
#                 try:
#                     value = float(match.group(1).replace(",", ""))
#                     if 1 <= value <= 10_00_000:
#                         amounts.append(value)
#                 except:
#                     pass

#         return max(amounts) if amounts else None

#     # ---------------- DATE EXTRACTION -----------------
#     def extract_date(self, text: str) -> Optional[str]:

#         patterns = [
#             r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
#             r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
#             r"(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\,?\s*\d{2,4})",
#             r"(date|bill date|invoice date)[\s:]*([0-9\-/]+)",
#         ]

#         for p in patterns:
#             m = re.search(p, text, re.IGNORECASE)
#             if m:
#                 date_str = m.group(1) if len(m.groups()) == 1 else m.group(2)
#                 parsed = self._parse_date(date_str)
#                 if parsed:
#                     return parsed

#         return None

#     def _parse_date(self, date_str: str) -> Optional[str]:
#         """Try multiple date formats."""

#         fmts = [
#             "%d-%m-%Y", "%d/%m/%Y",
#             "%d-%m-%y", "%d/%m/%y",
#             "%Y-%m-%d", "%Y/%m/%d",
#             "%d %b %Y", "%d %B %Y",
#             "%d %b, %Y", "%d %B, %Y",
#         ]

#         for f in fmts:
#             try:
#                 dt = datetime.strptime(date_str.strip(), f)
#                 return dt.date().isoformat()
#             except:
#                 continue

#         return None

#     # ---------------- MERCHANT EXTRACTION -----------------
#     def extract_merchant(self, text: str) -> Optional[str]:
#         """Extract merchant name from top lines."""

#         lines = [l.strip() for l in text.split("\n") if l.strip()][:5]

#         for line in lines:
#             if len(line) < 3:
#                 continue

#             # Look for company keywords
#             if any(k in line.lower() for k in ["pvt", "ltd", "store", "mart", "shop", "cafe", "restaurant"]):
#                 return line

#             # All caps merchant names
#             if line.isupper() and 3 < len(line) < 30:
#                 return line

#         return None

#     # ---------------- TOTAL LABEL EXTRACTION -----------------
#     def find_total_label(self, text: str) -> Optional[str]:
#         labels = ["total", "grand total", "net amount", "amount payable", "final amount"]

#         for line in text.split("\n"):
#             ll = line.lower()
#             if any(label in ll for label in labels):
#                 return line.strip()

#         return None
# core/ocr_processor.py
"""
OCRProcessor - production-ready Tesseract OCR helper.

Features:
 - Uses pytesseract with configurable tesseract binary path (via core.config.settings.TESSERACT_PATH)
 - Preprocess images (grayscale, denoise, adaptive threshold, optional deskew)
 - Returns text, per-word confidences, bounding boxes and basic processing metadata
 - Helpers to extract merchant, date, total amount and raw lines
 - Optional PDF -> images support via pdf2image (if installed)
"""

import os
import time
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

import numpy as np
from PIL import Image, ImageOps
import pytesseract
import cv2

# config helper (simple)
try:
    from core.config import settings
except Exception:
    class _Dummy:
        TESSERACT_PATH = ""
        MODELS_DIR = "models"
    settings = _Dummy()


# if user provided Tesseract path in settings, use it
if getattr(settings, "TESSERACT_PATH", None):
    if os.path.exists(settings.TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH


# ============================
# Utilities
# ============================
def _to_float_safe(s: str) -> Optional[float]:
    if s is None:
        return None
    try:
        ns = s.replace(",", "").strip()
        return float(ns)
    except Exception:
        return None


def _normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# ============================
# OCR Processor
# ============================
class OCRProcessor:
    def __init__(self, tesseract_config: str = "--oem 3 --psm 6", deskew: bool = True):
        """
        tesseract_config: string passed to pytesseract (e.g. "--oem 3 --psm 6")
        deskew: try to deskew image for better OCR
        """
        self.tesseract_config = tesseract_config
        self.deskew = deskew

    # -------------------------
    # Public: process a PIL.Image or path to image/pdf
    # -------------------------
    def process_document(self, image: Image.Image) -> Dict[str, Any]:
        """
        Run OCR on a single PIL.Image and return structured result:
        {
           success: bool,
           text: str,
           lines: List[str],
           words: List[ {text, conf, left, top, width, height} ],
           confidence: float,   # average word confidence
           processing_time: float
        }
        """
        try:
            t0 = time.time()
            # Ensure RGB
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Convert to numpy for OpenCV processing
            img_np = np.array(image)

            # Preprocess
            proc = self.preprocess_image(img_np)

            # Optionally deskew
            if self.deskew:
                proc = self._deskew(proc)

            # Run OCR (full text)
            text = pytesseract.image_to_string(proc, config=self.tesseract_config)

            # Word-level data (boxes + conf)
            try:
                data = pytesseract.image_to_data(proc, output_type=pytesseract.Output.DICT, config=self.tesseract_config)
            except Exception:
                # fallback: no per-word data
                data = {"text": [], "conf": []}

            words = []
            confidences: List[float] = []
            n = len(data.get("text", []))
            for i in range(n):
                w = data.get("text", [None] * n)[i]
                conf = data.get("conf", [None] * n)[i]
                left = data.get("left", [None] * n)[i]
                top = data.get("top", [None] * n)[i]
                width = data.get("width", [None] * n)[i]
                height = data.get("height", [None] * n)[i]
                if w is None or str(w).strip() == "":
                    continue
                try:
                    cval = float(conf)
                    if cval >= 0:
                        confidences.append(cval)
                except Exception:
                    cval = None
                words.append({
                    "text": w,
                    "conf": cval,
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height
                })

            avg_conf = float(sum(confidences) / len(confidences)) if confidences else 0.0
            t1 = time.time()

            # Build line list (split and clean)
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

            return {
                "success": True,
                "text": text,
                "lines": lines,
                "words": words,
                "confidence": round(avg_conf, 2),
                "processing_time": round(t1 - t0, 4),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "lines": [],
                "words": [],
                "confidence": 0.0,
                "processing_time": 0.0,
            }

    # -------------------------
    # Preprocessing helpers
    # -------------------------
    def preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """
        img: numpy array (BGR or grayscale)
        returns single-channel (grayscale) image ready for OCR
        """
        # convert if color
        if len(img.shape) == 3 and img.shape[2] == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # resize if very large (helps speed)
        h, w = gray.shape[:2]
        max_dim = 2000
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        # denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=10)

        # adaptive threshold helps for many receipts
        try:
            # apply bilateral filter then adaptive threshold
            blur = cv2.GaussianBlur(denoised, (3, 3), 0)
            thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 11, 2)
        except Exception:
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # morphological closing to join broken chars
        kernel = np.ones((1, 1), np.uint8)
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        return morph

    def _deskew(self, img: np.ndarray) -> np.ndarray:
        """Attempt simple deskew using moments / Hough lines; returns deskewed image"""
        try:
            coords = np.column_stack(np.where(img > 0))
            if coords.size == 0:
                return img
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            # rotate
            (h, w) = img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return rotated
        except Exception:
            return img

    # -------------------------
    # PDF → images (optional)
    # -------------------------
    def pdf_to_images(self, pdf_path: str, dpi: int = 200) -> List[Image.Image]:
        """
        Convert PDF pages to PIL.Images using pdf2image (optional).
        Requires `pdf2image` and system `poppler` installed.
        """
        try:
            from pdf2image import convert_from_path
        except Exception as e:
            raise RuntimeError("pdf2image is required for PDF support: pip install pdf2image") from e

        images = convert_from_path(pdf_path, dpi=dpi)
        return images

    # -------------------------
    # High-level: process PDF file (merge pages OCR text)
    # -------------------------
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        imgs = self.pdf_to_images(pdf_path)
        all_text = []
        all_lines = []
        confidences = []
        total_time = 0.0

        for img in imgs:
            res = self.process_document(img)
            if res.get("success"):
                all_text.append(res.get("text", ""))
                all_lines.extend(res.get("lines", []))
                if res.get("confidence"):
                    confidences.append(res.get("confidence", 0.0))
                total_time += res.get("processing_time", 0.0)
            else:
                # include error context but continue
                all_text.append("")
        avg_conf = float(sum(confidences) / len(confidences)) if confidences else 0.0
        return {
            "success": True,
            "text": "\n".join(all_text),
            "lines": all_lines,
            "confidence": round(avg_conf, 2),
            "processing_time": round(total_time, 4),
        }

    # -------------------------
    # Structured extraction helpers
    # -------------------------
    def extract_bill_details(self, text: str) -> Dict[str, Any]:
        """
        Returns:
        { merchant, date, total_amount, total_label_line, lines }
        """
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return {
            "merchant": self.extract_merchant(text, lines),
            "date": self.extract_date(text, lines),
            "total_amount": self.extract_amount(text, lines),
            "total_label": self.find_total_label(text, lines),
            "lines": lines
        }

    def extract_amount(self, text: str, lines: Optional[List[str]] = None) -> Optional[float]:
        """
        Return most likely grand total amount found in the text (float) or None.
        Strategy:
         - search for common total keywords in bottom region
         - fallback to last numeric value in last few lines
        """
        if lines is None:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        PRICE_RE = r"₹?\s*([\d{1,3}(?:,\d{3})]*\d+(?:\.\d{1,2})?)"
        # search bottom region (last 12 lines)
        bottom = lines[-12:]
        for ln in reversed(bottom):
            m = re.search(r"(total|grand total|net amount|amount payable|amount due|balance|bill total)[^\d\r\n\-]*([\d,]+\.\d{1,2}|\d+)", ln, re.IGNORECASE)
            if m:
                val = m.group(2)
                return _to_float_safe(val)
            # fallback: detect last numeric
            m2 = re.search(r"([\d,]+\.\d{1,2}|\d+)\s*$", ln)
            if m2:
                return _to_float_safe(m2.group(1))
        # last resort: search whole text for amounts, return max
        all_nums = re.findall(r"([\d,]+\.\d{1,2}|\d+)", text)
        nums = [ _to_float_safe(n) for n in all_nums if _to_float_safe(n) is not None ]
        return max(nums) if nums else None

    def find_total_label(self, text: str, lines: Optional[List[str]] = None) -> Optional[str]:
        if lines is None:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        labels = ["total", "grand total", "net amount", "amount payable", "final amount", "amount due", "bill total"]
        for ln in reversed(lines[-16:]):
            for lab in labels:
                if lab in ln.lower():
                    return ln
        return None

    def extract_date(self, text: str, lines: Optional[List[str]] = None) -> Optional[str]:
        if lines is None:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        date_patterns = [
            r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            r"(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s*\d{2,4})",
        ]
        for ln in lines[:16]:
            for p in date_patterns:
                m = re.search(p, ln, re.IGNORECASE)
                if m:
                    candidate = m.group(1)
                    parsed = self._try_parse_date(candidate)
                    if parsed:
                        return parsed
                    else:
                        return candidate
        return None

    def _try_parse_date(self, s: str) -> Optional[str]:
        fmts = ["%d-%m-%Y","%d/%m/%Y","%Y-%m-%d","%d-%m-%y","%d/%m/%y","%d %b %Y","%d %B %Y","%d %b, %Y"]
        for f in fmts:
            try:
                dt = datetime.strptime(s.strip(), f)
                return dt.date().isoformat()
            except Exception:
                continue
        return None

    def extract_merchant(self, text: str, lines: Optional[List[str]] = None) -> Optional[str]:
        if lines is None:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        # Heuristics: look at first 6 lines; prefer lines containing keywords or all caps names
        for ln in lines[:6]:
            ll = ln.strip()
            if len(ll) < 3:
                continue
            low = ll.lower()
            if any(k in low for k in ["pvt", "ltd", "store", "mart", "shop", "cafe", "restaurant", "supermarket"]):
                return _normalize_spaces(ll)
            if ll.isupper() and 3 < len(ll) < 40:
                return _normalize_spaces(ll)
        # fallback: first meaningful line
        for ln in lines[:6]:
            if len(ln.strip()) > 2:
                return _normalize_spaces(ln)
        return None

# EOF
