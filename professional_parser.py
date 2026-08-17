import os
import re
import time
import logging
import tracemalloc
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, List, Dict, Any, Tuple
import pdfplumber

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("parser.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AdvancedMedicalPDFParser")

# Graceful Tesseract setup
OCR_AVAILABLE = False
try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    OCR_AVAILABLE = True
    logger.info("pytesseract and PIL loaded successfully. Advanced OCR features enabled.")
except ImportError:
    logger.warning("pytesseract or PIL is not installed. OCR will output layout-placeholder notes.")

class AdvancedQualityTracker:
    """Tracks rich metrics, execution profile, and error logging for Quality Reporting."""
    def __init__(self):
        self.start_time = 0
        self.end_time = 0
        self.peak_memory_mb = 0.0
        self.total_pages = 0
        self.parsed_pages = 0
        self.ocr_fallbacks = 0
        self.tables_extracted = 0
        self.tables_by_class = Counter()
        self.figures_extracted = 0
        self.columns_processed = 0
        self.errors = []
        
    def start(self):
        self.start_time = time.perf_counter()
        tracemalloc.start()
        
    def stop(self):
        self.end_time = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        self.peak_memory_mb = peak / (1024 * 1024)
        tracemalloc.stop()
        
    def elapsed_time(self):
        return self.end_time - self.start_time
        
    def generate_report(self, output_path="parsing_quality_report.md"):
        accuracy = (self.parsed_pages / self.total_pages * 100) if self.total_pages > 0 else 0
        
        report = f"""# 📄 Advanced PDF Parsing Quality & Benchmark Report

## 📊 Summary Performance Metrics
- **Total Pages Analyzed**: {self.total_pages}
- **Parsing Success Rate**: {self.parsed_pages}/{self.total_pages} ({accuracy:.1f}%)
- **Region-based OCR Operations**: {self.ocr_fallbacks}
- **Figures / Drawings Extracted**: {self.figures_extracted}
- **Tables Extracted**: {self.tables_extracted}
  * Medication Tables: {self.tables_by_class.get("Medication Table", 0)}
  * Diagnostic Tables: {self.tables_by_class.get("Diagnostic Table", 0)}
  * General Tables: {self.tables_by_class.get("General Table", 0)}

## ⚡ Runtime Performance Profile
- **Total Execution Time**: {self.elapsed_time():.2f} seconds
- **Throughput Rate**: {(self.elapsed_time() / self.total_pages):.2f} seconds/page
- **Peak RAM Allocation**: {self.peak_memory_mb:.2f} MB

## 🛠️ Layout & Parsing Structure
- **Multi-Column Segmentation Blocks**: {self.columns_processed}
- **Critical Errors Logged**: {len(self.errors)}
"""
        if self.errors:
            report += "\n### ⚠️ Parsing Issues & Warning Log\n"
            for err in self.errors:
                report += f"- Page {err.get('page')}: {err.get('message')} [Type: {err.get('type')}]\n"
        else:
            report += "\n✅ **All layout pages, table matrices, and text elements parsed successfully.**\n"
            
        report += "\n*Generated automatically by AdvancedMedicalPDFParser Engine.*"
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info(f"Advanced quality report successfully saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to write advanced quality report: {str(e)}")

# Compatibility Alias
QualityTracker = AdvancedQualityTracker

class HierarchicalOutlineStack:
    """Manages Chapter -> Section -> Subsection hierarchy mapping during parsing."""
    def __init__(self):
        self.stack = []  # List of tuples: (level_int, title_str)
        self.document_title = "WHO Guidelines"
        
    def set_document_title(self, title):
        if title:
            self.document_title = title.strip()
            
    def update_heading(self, level, text):
        """Updates the stack by popping lower or equal hierarchy levels."""
        text = text.strip()
        # Keep only levels higher than current level
        self.stack = [item for item in self.stack if item[0] < level]
        self.stack.append((level, text))
        
    def get_metadata(self):
        """Returns structured metadata of the current hierarchy position."""
        chapter = "Unknown"
        section = "Unknown"
        subsection = "Unknown"
        
        for level, text in self.stack:
            if level == 1:
                chapter = text
            elif level == 2:
                section = text
            elif level == 3:
                subsection = text
                
        return {
            "document_title": self.document_title,
            "chapter": chapter,
            "section": section,
            "subsection": subsection,
            "hierarchy_path": " > ".join([item[1] for item in self.stack]) if self.stack else "General"
        }

def extract_outline_hierarchy_map(pdf_path):
    """Builds a map of page number -> active section/chapter based on PDF Bookmarks outline."""
    hierarchy_map = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Build index-based page lookup (page index 0 = page number 1)
            total_pages = len(pdf.pages)
            
            # Extract outlines if bookmarks exist
            outlines = []
            try:
                outlines = list(pdf.doc.get_outlines())
            except:
                pass
                
            outline_items = []
            for item in outlines:
                level = item[0]
                title = item[1]
                dest = item[2]
                
                page_num = None
                # pdfminer destinations can be: int (page index), list [page_ref, ...], or PDFPage
                if isinstance(dest, int):
                    page_num = dest + 1  # 0-indexed to 1-indexed
                elif isinstance(dest, list) and len(dest) > 0:
                    dest_obj = dest[0]
                    if isinstance(dest_obj, int):
                        page_num = dest_obj + 1
                    else:
                        # Resolve indirect reference via pdfminer
                        try:
                            resolved = pdf.doc.get_page_number(dest_obj)
                            page_num = resolved + 1
                        except:
                            pass
                        
                if page_num:
                    outline_items.append((page_num, level, title))
            
            # Sort bookmarks by page number
            outline_items = sorted(outline_items, key=lambda x: x[0])
            
            active_chapter = "General Context"
            active_section = "General Section"
            active_subsection = "General Subsection"
            
            for page in pdf.pages:
                p_num = page.page_number
                
                # Check for headings starting on this page
                for o_pnum, o_level, o_title in outline_items:
                    if o_pnum == p_num:
                        if o_level == 1:
                            active_chapter = o_title
                            active_section = "General Section"
                            active_subsection = "General Subsection"
                        elif o_level == 2:
                            active_section = o_title
                            active_subsection = "General Subsection"
                        elif o_level >= 3:
                            active_subsection = o_title
                            
                hierarchy_map[p_num] = {
                    "chapter": active_chapter,
                    "section": active_section,
                    "subsection": active_subsection
                }
    except Exception as e:
        logger.warning(f"Could not extract outline hierarchy map dynamically: {str(e)}")
        
    return hierarchy_map

def format_table_as_markdown(table_data):
    """
    Formats raw list-of-lists table data to a clean Markdown table,
    handling empty and merged cell representations gracefully.
    """
    if not table_data or not table_data[0]:
        return ""
    
    clean_table = []
    max_cols = max(len(row) for row in table_data)
    
    # Clean up row cells and resolve None values from merged cells
    for row in table_data:
        clean_row = []
        for cell in row:
            if cell is None:
                clean_row.append("")
            else:
                # Remove internal newlines and whitespace
                val = str(cell).replace("\n", " ").strip()
                clean_row.append(val)
        
        # Pads rows to match max column length if irregular
        while len(clean_row) < max_cols:
            clean_row.append("")
        clean_table.append(clean_row)
        
    headers = clean_table[0]
    # Handle empty headers
    headers = [col if col else f"Column {i+1}" for i, col in enumerate(headers)]
    rows = clean_table[1:]
    
    markdown = "\n"
    markdown += "| " + " | ".join(headers) + " |\n"
    markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    for row in rows:
        markdown += "| " + " | ".join(row) + " |\n"
    markdown += "\n"
    return markdown

def detect_columns(page, min_gap_pts=30):
    """
    Analyzes horizontal text distribution to detect if the page has a two-column layout.
    Returns list of cropping bounding boxes [(x0, top, x1, bottom)] representing columns.
    """
    chars = page.chars
    if not chars:
        return None
        
    width = page.width
    height = page.height
    
    # Calculate text presence along horizontal bins (1-point wide)
    bins = [0] * int(width + 1)
    for c in chars:
        x0 = int(max(0, c["x0"]))
        x1 = int(min(width, c["x1"]))
        for x in range(x0, x1 + 1):
            if x < len(bins):
                bins[x] += 1
                
    # Search for a continuous empty gap (bin count is 0 or near 0) in the middle 30%-70% region
    start_mid = int(width * 0.3)
    end_mid = int(width * 0.7)
    
    current_gap_start = None
    max_gap_start = None
    max_gap_width = 0
    
    for x in range(start_mid, end_mid):
        # We consider a bin empty if it has <= 1 character overlap (robust against minor noise)
        if bins[x] <= 1:
            if current_gap_start is None:
                current_gap_start = x
        else:
            if current_gap_start is not None:
                gap_w = x - current_gap_start
                if gap_w > max_gap_width:
                    max_gap_width = gap_w
                    max_gap_start = current_gap_start
                current_gap_start = None
                
    # If the gap at the end of the loop is the largest
    if current_gap_start is not None:
        gap_w = end_mid - current_gap_start
        if gap_w > max_gap_width:
            max_gap_width = gap_w
            max_gap_start = current_gap_start
            
    # If we found a significant gap, it's a two-column layout
    if max_gap_width >= min_gap_pts:
        mid_point = max_gap_start + (max_gap_width // 2)
        # Left column, Right column coordinates
        return [
            (0, 0, mid_point, height),
            (mid_point, 0, width, height)
        ]
    return None

def dynamic_margin_analysis(pdf_path, num_samples=15):
    """
    Scans document samples to identify the exact bounding box of running headers/footers
    by matching repeating text lines. Returns Y-crop bounds.
    """
    logger.info("Initializing dynamic margin analysis...")
    top_line_ys = []
    bottom_line_ys = []
    repeating_headers = Counter()
    repeating_footers = Counter()
    page_height = 842.0
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            step = max(1, total // num_samples)
            sample_indices = list(range(0, total, step))[:num_samples]
            
            for idx in sample_indices:
                page = pdf.pages[idx]
                page_height = page.height
                words = page.extract_words()
                
                lines = {}
                for w in words:
                    y_coord = round(w["top"], 1)
                    found = False
                    for k in lines.keys():
                        if abs(k - w["top"]) < 4:
                            lines[k].append(w)
                            found = True
                            break
                    if not found:
                        lines[w["top"]] = [w]
                        
                height_15_percent = page_height * 0.15
                height_85_percent = page_height * 0.85
                
                for y, w_list in lines.items():
                    w_list = sorted(w_list, key=lambda x: x["x0"])
                    line_text = " ".join([w["text"] for w in w_list]).strip()
                    if len(line_text) < 5:
                        continue
                    if y < height_15_percent:
                        repeating_headers[line_text] += 1
                        top_line_ys.append(y)
                    elif y > height_85_percent:
                        repeating_footers[line_text] += 1
                        bottom_line_ys.append(y)
                        
        actual_headers = {text for text, count in repeating_headers.items() if count >= max(2, num_samples * 0.3)}
        actual_footers = {text for text, count in repeating_footers.items() if count >= max(2, num_samples * 0.3)}
        
        header_crop_limit = page_height * 0.06
        footer_crop_limit = page_height * 0.94
        
        if actual_headers and top_line_ys:
            header_crop_limit = max(top_line_ys) + 8.0
        if actual_footers and bottom_line_ys:
            footer_crop_limit = min(bottom_line_ys) - 8.0
            
        logger.info(f"Dynamic Crop Bounds determined: Header Limit = {header_crop_limit:.1f}pt, Footer Limit = {footer_crop_limit:.1f}pt")
        return {
            "header_limit": header_crop_limit,
            "footer_limit": footer_crop_limit,
            "repeating_headers": actual_headers,
            "repeating_footers": actual_footers,
            "page_height": page_height
        }
    except Exception as e:
        logger.error(f"Failed to analyze dynamic margins: {str(e)}")
        return {"header_limit": 50, "footer_limit": 790, "repeating_headers": set(), "repeating_footers": set(), "page_height": 842}

def recursive_xy_cut(elements, bbox, tracker, horizontal_threshold=15, vertical_threshold=25):
    """
    Recursively segments page elements (words/rects) into layout columns and paragraphs
    using projection profile splits. Returns list of sorted elements in logical reading order.
    """
    x0, top, x1, bottom = bbox
    
    # Filter elements within this bounding box
    box_elements = []
    for el in elements:
        if (el["x0"] >= x0 - 1 and el["x1"] <= x1 + 1 and 
            el["top"] >= top - 1 and el["bottom"] <= bottom + 1):
            box_elements.append(el)
            
    if not box_elements:
        return []
        
    # Analyze horizontal (Y-axis) projection first
    y_bins = [0] * int(bottom - top + 2)
    for el in box_elements:
        y0_idx = int(max(0, el["top"] - top))
        y1_idx = int(min(len(y_bins) - 1, el["bottom"] - top))
        for y in range(y0_idx, y1_idx + 1):
            y_bins[y] += 1
            
    horizontal_gaps = []
    gap_start = None
    for y in range(len(y_bins)):
        if y_bins[y] == 0:
            if gap_start is None:
                gap_start = y
        else:
            if gap_start is not None:
                gap_w = y - gap_start
                if gap_w >= horizontal_threshold:
                    horizontal_gaps.append((gap_start + top, y + top))
                gap_start = None
                
    if horizontal_gaps:
        largest_gap = max(horizontal_gaps, key=lambda g: g[1] - g[0])
        split_y = largest_gap[0] + (largest_gap[1] - largest_gap[0]) / 2
        
        top_box = (x0, top, x1, split_y)
        bottom_box = (x0, split_y, x1, bottom)
        
        return (recursive_xy_cut(box_elements, top_box, tracker, horizontal_threshold, vertical_threshold) + 
                recursive_xy_cut(box_elements, bottom_box, tracker, horizontal_threshold, vertical_threshold))
                
    # Analyze vertical (X-axis) projection
    x_bins = [0] * int(x1 - x0 + 2)
    for el in box_elements:
        x0_idx = int(max(0, el["x0"] - x0))
        x1_idx = int(min(len(x_bins) - 1, el["x1"] - x0))
        for x in range(x0_idx, x1_idx + 1):
            x_bins[x] += 1
            
    vertical_gaps = []
    gap_start = None
    for x in range(len(x_bins)):
        if x_bins[x] == 0:
            if gap_start is None:
                gap_start = x
        else:
            if gap_start is not None:
                gap_w = x - gap_start
                if gap_w >= vertical_threshold:
                    vertical_gaps.append((gap_start + x0, x + x0))
                gap_start = None
                
    if vertical_gaps:
        tracker.columns_processed += 1
        largest_gap = max(vertical_gaps, key=lambda g: g[1] - g[0])
        split_x = largest_gap[0] + (largest_gap[1] - largest_gap[0]) / 2
        
        left_box = (x0, top, split_x, bottom)
        right_box = (split_x, top, x1, bottom)
        
        return (recursive_xy_cut(box_elements, left_box, tracker, horizontal_threshold, vertical_threshold) + 
                recursive_xy_cut(box_elements, right_box, tracker, horizontal_threshold, vertical_threshold))
                
    sorted_leaves = sorted(box_elements, key=lambda e: (round(e["top"], 1), e["x0"]))
    return sorted_leaves

def preprocess_image_for_ocr(pil_img):
    """Enhances image quality to 300+ DPI equivalent scale and applies thresholding filters."""
    img_gray = pil_img.convert("L")
    w, h = img_gray.size
    img_scaled = img_gray.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
    enhancer = ImageEnhance.Contrast(img_scaled)
    img_contrast = enhancer.enhance(2.0)
    img_bin = img_contrast.point(lambda p: 255 if p > 128 else 0)
    return img_bin

def setup_tesseract_path(custom_cmd: Optional[str] = None) -> bool:
    """
    Automatically search for and configure Tesseract executable path.
    Returns True if Tesseract executable is found and verified.
    """
    if not OCR_AVAILABLE:
        return False

    if custom_cmd and os.path.exists(custom_cmd):
        try:
            pytesseract.pytesseract.tesseract_cmd = custom_cmd
            return True
        except Exception:
            pass

    env_path = os.environ.get("TESSERACT_CMD")
    if env_path and os.path.exists(env_path):
        try:
            pytesseract.pytesseract.tesseract_cmd = env_path
            return True
        except Exception:
            pass

    import shutil
    if shutil.which("tesseract"):
        return True

    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\FreeComp\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract"
    ]
    for p in common_paths:
        if os.path.exists(p):
            try:
                pytesseract.pytesseract.tesseract_cmd = p
                return True
            except Exception:
                pass

    return False

def extract_region_ocr(page, bbox):
    """Performs localized OCR on a specific crop box instead of the full page, supporting multi-language."""
    if not OCR_AVAILABLE or not setup_tesseract_path():
        # Gracefully skip OCR if Tesseract executable is unavailable — do NOT generate error nodes
        return ""

    try:
        cropped = page.crop(bbox)
        pil_img = cropped.to_image(resolution=300).original
        processed_img = preprocess_image_for_ocr(pil_img)
        # Use English and Arabic OCR fallback
        text = pytesseract.image_to_string(processed_img, lang="eng+ara")
        return text.strip()
    except Exception as e:
        logger.warning(f"Region-based OCR gracefully skipped at bbox {bbox}: {str(e)}")
        return ""

def classify_table(headers, sample_rows):
    """Classifies a table into Medical category types using keyword heuristics."""
    content_text = (" ".join(headers) + " " + " ".join([" ".join(map(str, row)) for row in sample_rows])).lower()
    
    medication_keywords = ["insulin", "dose", "mg", "metformin", "drug", "medicine", "second-line", "treatment", "sulphonylurea"]
    diagnostic_keywords = ["diagnosis", "criteria", "symptom", "hba1c", "blood glucose", "glucose", "glycaemia", "fasting"]
    
    if any(kw in content_text for kw in medication_keywords):
        return "Medication Table"
    elif any(kw in content_text for kw in diagnostic_keywords):
        return "Diagnostic Table"
    return "General Table"

def parse_inline_elements(page, tracker, outline_stack, header_footer_metadata):
    """
    Processes all text, tables, figures and captions on a single page,
    sorting them in XY-Cut reading order and outputting structured markdown.
    """
    width = page.width
    height = page.height
    page_num = page.page_number
    
    os.makedirs("media", exist_ok=True)
    
    tables = page.find_tables()
    table_bboxes = [t.bbox for t in tables]
    
    images = page.images
    # Filter: Only extract images/figures that have width and height > 150 pt
    # This prevents extracting tiny icons, lines, or borders to the disk.
    image_bboxes = [(im["x0"], im["top"], im["x1"], im["bottom"]) for im in images if im["width"] > 150 and im["height"] > 150]
    
    # Exclude repeating header/footer texts
    def filter_hf_and_tables(obj):
        if "text" in obj:
            t = obj["text"].strip()
            if t in header_footer_metadata["repeating_headers"] or t in header_footer_metadata["repeating_footers"]:
                return False
        return True
        
    cleaned_page = page.filter(filter_hf_and_tables)
    
    # Extract words including extra attributes: size and fontname
    words = cleaned_page.extract_words(keep_blank_chars=False, extra_attrs=["size", "fontname"])
    
    # Apply Recursive XY-Cut Layout Analysis to order the words correctly
    # Calculate Y limits dynamically for mixed orientation pages (portrait/landscape)
    page_height_ref = header_footer_metadata.get("page_height", 842.0)
    h_ratio = header_footer_metadata.get("header_limit", 50.0) / page_height_ref
    f_ratio = (page_height_ref - header_footer_metadata.get("footer_limit", 790.0)) / page_height_ref
    
    page_header_limit = height * h_ratio
    page_footer_limit = height * (1 - f_ratio)
    
    page_bbox = (0, page_header_limit, width, page_footer_limit)
    sorted_words = recursive_xy_cut(words, page_bbox, tracker)
    
    # Reassemble words into logical lines
    lines = []
    current_line = []
    for w in sorted_words:
        if not current_line:
            current_line.append(w)
        else:
            if abs(current_line[-1]["top"] - w["top"]) < 4:
                current_line.append(w)
            else:
                lines.append(current_line)
                current_line = [w]
    if current_line:
        lines.append(current_line)
        
    # Analyze median font size for heading hierarchy
    body_size = 10.0
    all_sizes = [round(w.get("size", 10.0), 1) for w in sorted_words if w.get("size")]
    if all_sizes:
        body_size = Counter(all_sizes).most_common(1)[0][0]
        
    text_blocks = []
    for line in lines:
        line_sorted = sorted(line, key=lambda x: x["x0"])
        text = " ".join([w["text"] for w in line_sorted]).strip()
        if not text:
            continue
            
        # Get line characters average size and bold attributes
        avg_size = sum(w.get("size", body_size) for w in line_sorted) / len(line_sorted)
        is_bold = False
        font_names = [w.get("fontname", "").lower() for w in line_sorted if w.get("fontname")]
        if font_names:
            is_bold = any(any(bk in fn for bk in ["bold", "heavy", "black", "semibold"]) for fn in font_names)
            
        is_heading = False
        heading_level = 0
        heading_prefix = ""
        
        numbered_pattern = re.match(r"^(\d+(\.\d+)*)\s+[A-Z]", text)
        chapter_pattern = re.match(r"^(chapter|section|appendix)\s+[\d\w\.]+", text, re.IGNORECASE)
        
        # Only tag as explicit markdown heading if it meets strong structural criteria,
        # avoiding naive tagging of multi-line titles or bold body lines.
        if chapter_pattern:
            is_heading = True
            heading_level = 1
            heading_prefix = "## "
        elif numbered_pattern and not text.endswith("."):
            is_heading = True
            heading_level = 2
            heading_prefix = "### "
        elif avg_size > body_size * 1.35 and not text.endswith("."):
            is_heading = True
            heading_level = 1
            heading_prefix = "## "
            
        is_list = False
        list_match = re.match(r"^(\s*)([\-\*\•]|\d+\.)(\s+)(.*)", text)
        if list_match:
            is_list = True
            indent = int(line_sorted[0]["x0"] // 35)
            text = "  " * indent + "- " + list_match.group(4)
            
        if is_heading and not is_list:
            text = heading_prefix + text
            outline_stack.update_heading(heading_level, text.lstrip("# "))
            
        text_blocks.append({
            "type": "text",
            "top": line_sorted[0]["top"],
            "bottom": line_sorted[0]["bottom"],
            "x0": line_sorted[0]["x0"],
            "x1": line_sorted[-1]["x1"],
            "content": text
        })
        
    # Process Tables
    table_blocks = []
    for idx, t in enumerate(tables):
        try:
            raw_data = t.extract()
            headers = [str(cell or "").strip() for cell in raw_data[0]] if raw_data else []
            rows = [[str(cell or "").strip() for cell in row] for row in raw_data[1:]] if len(raw_data) > 1 else []
            table_class = classify_table(headers, rows[:3])
            tracker.tables_by_class[table_class] += 1
            tracker.tables_extracted += 1

            md_table = format_table_as_markdown(raw_data)

            caption = ""
            for tb in text_blocks:
                if (abs(tb["bottom"] - t.bbox[1]) < 35 or abs(tb["top"] - t.bbox[3]) < 35) and "table" in tb["content"].lower():
                    caption = tb["content"].lstrip("# ")
                    break

            table_content = ""
            if caption:
                table_content += f"\n**Table Caption**: *{caption}* (Class: {table_class})\n"
            table_content += md_table

            table_blocks.append({
                "type": "table",
                "top": round(t.bbox[1], 2),
                "bottom": round(t.bbox[3], 2),
                "x0": round(t.bbox[0], 2),
                "x1": round(t.bbox[2], 2),
                "bbox": (round(t.bbox[0], 2), round(t.bbox[1], 2), round(t.bbox[2], 2), round(t.bbox[3], 2)),
                "headers": headers,
                "rows": rows,
                "caption": caption,
                "table_class": table_class,
                "content": table_content
            })
        except Exception as e:
            err_msg = f"Table {idx+1} parse failed: {str(e)}"
            logger.error(err_msg)
            tracker.errors.append({"page": page_num, "type": "table_error", "message": err_msg})

    # Process Figures
    figure_blocks = []
    for idx, im in enumerate(images):
        # Filter: Only extract images/figures that have width and height > 50 pt
        if im.get("width", 0) > 50 and im.get("height", 0) > 50:
            try:
                raw_box = (im["x0"], im["top"], im["x1"], im["bottom"])
                # Clamp coordinates strictly within parent page bounds
                clamped_box = (
                    max(0.0, min(width - 1.0, raw_box[0])),
                    max(0.0, min(height - 1.0, raw_box[1])),
                    max(1.0, min(width, raw_box[2])),
                    max(1.0, min(height, raw_box[3]))
                )
                if (clamped_box[2] - clamped_box[0]) > 20 and (clamped_box[3] - clamped_box[1]) > 20:
                    fig_path = f"media/figure_page_{page_num}_{idx+1}.png"
                    os.makedirs("media", exist_ok=True)
                    cropped_im = page.crop(clamped_box)
                    cropped_im.to_image(resolution=150).save(fig_path)
                    tracker.figures_extracted += 1

                    caption = ""
                    for tb in text_blocks:
                        if (abs(tb["bottom"] - clamped_box[1]) < 35 or abs(tb["top"] - clamped_box[3]) < 35) and any(kw in tb["content"].lower() for kw in ["figure", "fig.", "chart", "image"]):
                            caption = tb["content"].lstrip("# ")
                            break

                    caption_str = caption if caption else f"Figure extracted from Page {page_num}, Area {idx+1}"
                    fig_number = f"Figure {idx+1}"
                    if "fig." in caption_str.lower() or "figure" in caption_str.lower():
                        m_f = re.search(r"((?:figure|fig\.)\s*[\dA-Z]+)", caption_str, re.IGNORECASE)
                        if m_f:
                            fig_number = m_f.group(1)

                    fig_content = f"\n![{caption_str}]({fig_path})\n*Caption*: *{caption_str}*\n"

                    figure_blocks.append({
                        "type": "figure",
                        "top": round(clamped_box[1], 2),
                        "bottom": round(clamped_box[3], 2),
                        "x0": round(clamped_box[0], 2),
                        "x1": round(clamped_box[2], 2),
                        "bbox": (round(clamped_box[0], 2), round(clamped_box[1], 2), round(clamped_box[2], 2), round(clamped_box[3], 2)),
                        "figure_number": fig_number,
                        "caption": caption_str,
                        "image_path": fig_path,
                        "content": fig_content
                    })
            except Exception as e:
                logger.warning(f"Failed to render figure crop at page {page_num}, box {im}: {str(e)}")

    # Filter text falling inside table bboxes
    filtered_text_blocks = []
    for tb in text_blocks:
        inside_table = False
        for t_bbox in table_bboxes:
            if tb["top"] >= t_bbox[1] - 2 and tb["bottom"] <= t_bbox[3] + 2:
                inside_table = True
                break
        if not inside_table:
            filtered_text_blocks.append(tb)

    all_blocks = sorted(filtered_text_blocks + table_blocks + figure_blocks, key=lambda x: x["top"])

    final_markdown = ""
    for block in all_blocks:
        final_markdown += block["content"] + "\n"

    # Apply intra-page hyphenation post-processing (e.g. glu-\ncose -> glucose)
    final_markdown = re.sub(r"(\w+)-\n(\w+)", r"\1\2", final_markdown)

    return final_markdown

def semantic_section_classifier(page_content):
    """Classifies the semantic category of the page content."""
    text_lower = page_content.lower()
    if "evidence" in text_lower or "literature" in text_lower or "pubmed" in text_lower:
        return "Clinical Evidence & Studies"
    elif "recommendation" in text_lower or "should" in text_lower or "contraindicated" in text_lower:
        return "Treatment Recommendation Guideline"
    elif "insulin" in text_lower or "dose" in text_lower or "regimen" in text_lower:
        return "Medication & Insulin Dosing Protocol"
    return "General Medical Context"

def process_page_worker(pdf_path, page_num, margin_meta, doc_title, outline_hierarchy_map):
    """Worker function executed in parallel child processes to process a single page."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num - 1]
            width = page.width
            height = page.height

            # Apply dynamic margin cropping
            page_height_ref = margin_meta.get("page_height", 842.0)
            h_ratio = margin_meta.get("header_limit", 50.0) / page_height_ref
            f_ratio = (page_height_ref - margin_meta.get("footer_limit", 790.0)) / page_height_ref

            page_header_limit = height * h_ratio
            page_footer_limit = height * (1 - f_ratio)

            cropped = page.crop((0, page_header_limit, width, page_footer_limit))
            raw_text = cropped.extract_text() or ""
            raw_clean = re.sub(r"\s+", " ", raw_text).strip()

            # Check for scanned page
            if len(raw_clean) < 120 and (page.images or page.rects):
                ocr_texts = []
                for img in page.images:
                    raw_box = (img["x0"], img["top"], img["x1"], img["bottom"])
                    clamped_box = (
                        max(0.0, min(width - 1.0, raw_box[0])),
                        max(0.0, min(height - 1.0, raw_box[1])),
                        max(1.0, min(width, raw_box[2])),
                        max(1.0, min(height, raw_box[3]))
                    )
                    ocr_result = extract_region_ocr(page, clamped_box)
                    ocr_texts.append(ocr_result)
                ocr_content = "\n\n".join(ocr_texts) if ocr_texts else "[Empty Scanned Page Content]"

                return {
                    "page_number": page_num,
                    "content": ocr_content,
                    "is_ocr": True,
                    "is_error": False,
                    "error_msg": "",
                    "tables_detected": 0,
                    "figures_detected": len(page.images),
                    "columns_processed": 0
                }

            # Process normal layout
            tracker_mock = AdvancedQualityTracker()
            outline_stack = HierarchicalOutlineStack()
            outline_stack.set_document_title(doc_title)

            # Extract bookmarks hierarchy dynamically
            h_info = outline_hierarchy_map.get(page_num, {"chapter": "Unknown", "section": "Unknown", "subsection": "Unknown"})
            outline_stack.update_heading(1, h_info["chapter"])
            outline_stack.update_heading(2, h_info["section"])
            outline_stack.update_heading(3, h_info["subsection"])

            md_content = parse_inline_elements(page, tracker_mock, outline_stack, margin_meta)

            hierarchy = outline_stack.get_metadata()
            arabic_chars = len(re.findall(r'[\u0600-\u06FF]', md_content))
            language = "Arabic" if arabic_chars > len(md_content) * 0.1 else "English"
            sem_class = semantic_section_classifier(md_content)

            col_split = detect_columns(cropped)
            layout_type = "two_column" if col_split else "single_column"

            is_fm = (page_num <= 6 and ("copyright" in md_content.lower() or "isbn" in md_content.lower() or "contents" in md_content.lower() or page_num <= 2))

            return {
                "page_number": page_num,
                "content": md_content,
                "is_ocr": False,
                "is_error": False,
                "error_msg": "",
                "tables_detected": len(page.find_tables()),
                "tables_by_class": dict(tracker_mock.tables_by_class),
                "figures_detected": len([im for im in page.images if im.get("width", 0) > 50 and im.get("height", 0) > 50]),
                "columns_processed": tracker_mock.columns_processed,
                "metadata_fields": {
                    "document_title": hierarchy["document_title"],
                    "chapter": hierarchy["chapter"],
                    "section": hierarchy["section"],
                    "subsection": hierarchy["subsection"],
                    "language": language,
                    "layout_type": layout_type,
                    "semantic_class": sem_class,
                    "is_front_matter": is_fm
                }
            }
    except Exception as e:
        return {
            "page_number": page_num,
            "content": f"[Critical Parsing Failure - Page {page_num}]",
            "is_ocr": False,
            "is_error": True,
            "error_msg": str(e),
            "tables_detected": 0,
            "figures_detected": 0,
            "columns_processed": 0
        }

def advanced_parse_pdf(pdf_path):
    """
    Ultimate Parallel PDF Parser Engine.
    """
    logger.info("Initializing Advanced Parallel PDF Parser...")
    tracker = AdvancedQualityTracker()
    tracker.start()
    
    if not os.path.exists(pdf_path):
        tracker.errors.append({"page": 0, "type": "file_not_found", "message": f"{pdf_path} not found."})
        tracker.stop()
        return None, tracker
        
    margin_meta = dynamic_margin_analysis(pdf_path)
    outline_hierarchy_map = extract_outline_hierarchy_map(pdf_path)
    
    doc_title = "WHO Guidelines"
    total_pages = 0
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            tracker.total_pages = total_pages
            
            # Extract document title
            first_page = pdf.pages[0]
            words = first_page.extract_words()
            if words:
                largest_word = max(words, key=lambda w: w.get("size", 10.0))
                title_words = [w["text"] for w in words if abs(w.get("size", 10.0) - largest_word.get("size", 10.0)) < 2]
                doc_title = " ".join(title_words)
                
        # Run multiprocessing executor for pages
        logger.info(f"Dispatching parallel execution workers for {total_pages} pages...")
        page_nums = list(range(1, total_pages + 1))
        
        parsed_results = []
        # Multi-process pool executor
        with ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(process_page_worker, pdf_path, num, margin_meta, doc_title, outline_hierarchy_map)
                for num in page_nums
            ]
            
            for f in futures:
                parsed_results.append(f.result())
                
        parsed_documents = []
        for res in sorted(parsed_results, key=lambda x: x["page_number"]):
            p_num = res["page_number"]
            
            # Aggregate stats from parallel workers into the main tracker
            tracker.tables_extracted += res.get("tables_detected", 0)
            tracker.figures_extracted += res.get("figures_detected", 0)
            tracker.columns_processed += res.get("columns_processed", 0)
            if res.get("is_ocr"):
                tracker.ocr_fallbacks += 1
            for cls, cnt in res.get("tables_by_class", {}).items():
                tracker.tables_by_class[cls] += cnt
                
            if res["is_error"]:
                tracker.errors.append({"page": p_num, "type": "page_critical", "message": res["error_msg"]})
                parsed_documents.append({
                    "page_number": p_num,
                    "content": res["content"],
                    "metadata": {
                        "source": os.path.basename(pdf_path),
                        "page_number": p_num,
                        "document_title": doc_title,
                        "chapter": "Error",
                        "section": "Error",
                        "subsection": "Error",
                        "is_ocr": False,
                        "language": "Unknown",
                        "word_count": 0,
                        "char_count": 0,
                        "has_tables": False,
                        "layout_type": "unknown",
                        "semantic_class": "Error Placeholder"
                    }
                })
                continue
                
            tracker.parsed_pages += 1
            tracker.columns_processed += res["columns_processed"]
            
            if res["is_ocr"]:
                parsed_documents.append({
                    "page_number": p_num,
                    "content": res["content"],
                    "metadata": {
                        "source": os.path.basename(pdf_path),
                        "page_number": p_num,
                        "document_title": doc_title,
                        "chapter": "Scanned Document",
                        "section": "OCR fallback",
                        "subsection": "OCR fallback",
                        "is_ocr": True,
                        "language": "English",
                        "word_count": len(res["content"].split()),
                        "char_count": len(res["content"]),
                        "has_tables": False,
                        "layout_type": "scanned_image",
                        "semantic_class": "Scanned Content"
                    }
                })
            else:
                m = res["metadata_fields"]
                parsed_documents.append({
                    "page_number": p_num,
                    "content": res["content"],
                    "metadata": {
                        "source": os.path.basename(pdf_path),
                        "page_number": p_num,
                        "document_title": m["document_title"],
                        "chapter": m["chapter"],
                        "section": m["section"],
                        "subsection": m["subsection"],
                        "is_ocr": False,
                        "language": m["language"],
                        "word_count": len(res["content"].split()),
                        "char_count": len(res["content"]),
                        "has_tables": "|\n|" in res["content"],
                        "layout_type": m["layout_type"],
                        "semantic_class": m["semantic_class"]
                    }
                })
                
        # 8. Apply cross-page boundary paragraph merging
        # If page ends in the middle of a sentence and next starts with lowercase, merge boundary
        for i in range(len(parsed_documents) - 1):
            doc1 = parsed_documents[i]
            doc2 = parsed_documents[i+1]
            
            content1 = doc1["content"].strip()
            content2 = doc2["content"].strip()
            
            # Check if doc1 ends with hyphen and doc2 starts with letter -> join cross-page hyphenated word
            hyphen_match = re.search(r"(\w+)-\s*$", content1)
            next_word_match = re.match(r"^\s*(\w+)", content2)
            
            if hyphen_match and next_word_match:
                merged_word = hyphen_match.group(1) + next_word_match.group(1)
                # Replace hyphen at tail of doc1 and prefix at head of doc2
                doc1["content"] = re.sub(r"(\w+)-\s*$", "", doc1["content"])
                doc2["content"] = re.sub(r"^\s*(\w+)", merged_word, doc2["content"])
                logger.info(f"Resolved cross-page hyphenation at boundary Page {p_num} -> {p_num+1} ({merged_word})")
                
    except Exception as pdf_err:
        logger.critical(f"Parser Engine failed to process PDF: {str(pdf_err)}")
        tracker.errors.append({"page": 0, "type": "pdf_critical", "message": str(pdf_err)})
        
    tracker.stop()
    tracker.generate_report()
    
    return parsed_documents, tracker

if __name__ == "__main__":
    pdf_filename = "9789241550284-eng.pdf"
    
    documents, tracker = advanced_parse_pdf(pdf_filename)
    
    if documents:
        print(f"\nAdvanced Parallel parsing completed successfully!")
        print(f"Elapsed Time: {tracker.elapsed_time():.2f} seconds")
        print(f"Peak RAM: {tracker.peak_memory_mb:.2f} MB")
        print("Details stored in parser.log and parsing_quality_report.md")
        
        sample = None
        for doc in documents:
            if doc["metadata"]["has_tables"] and doc["metadata"]["semantic_class"] == "Medication & Insulin Dosing Protocol":
                sample = doc
                break
                
        if sample:
            print(f"\n--- Output Sample: Page {sample['page_number']} ---")
            print(f"Hierarchical Path: {sample['metadata']['chapter']} -> {sample['metadata']['section']} -> {sample['metadata']['subsection']}")
            print(f"Semantic Class: {sample['metadata']['semantic_class']}")
            print(f"Content Preview (first 1000 chars):")
            print(sample["content"][:1000] + "\n...")
        else:
            print(f"\nPage 12 Content Preview:")
            print(documents[11]["content"][:1000])
