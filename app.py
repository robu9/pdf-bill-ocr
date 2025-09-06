import os
import re
import json
from PIL import Image
import fitz  # PyMuPDF
import pytesseract
from doctr.models import ocr_predictor
from doctr.io import DocumentFile

# Initialize docTR OCR model
model = ocr_predictor(pretrained=True)

def extract_data_from_text(text):
    """
    Extract structured invoice data from raw OCR text
    """
    data = {"invoice_no": None, "date": None, "vendor": None, "items": [], "total": None}

    # Flexible regex patterns for common invoice fields
    invoice_match = re.search(r"(Invoice|Bill|Inv)\s*(No|#|Number)?[:\-]?\s*(\w+)", text, re.I)
    if invoice_match:
        data["invoice_no"] = invoice_match.group(3)

    date_match = re.search(r"Date[:\-]?\s*([\d\/\-\.]+)", text, re.I)
    if date_match:
        data["date"] = date_match.group(1)

    vendor_match = re.search(r"(Vendor|From|Supplier|Billed To)[:\-]?\s*(.+)", text, re.I)
    if vendor_match:
        data["vendor"] = vendor_match.group(2).strip()

    total_match = re.search(r"(Total|Grand Total|Amount Due|Balance)[:\-]?\s*([\d\.,]+)", text, re.I)
    if total_match:
        data["total"] = float(total_match.group(2).replace(',', ''))

    # Extract items (lines with at least 3 numbers for qty, price, amount)
    lines = text.splitlines()
    for line in lines:
        numbers = re.findall(r"\d+(?:\.\d+)?", line)
        if len(numbers) >= 3:
            try:
                item = {
                    "name": re.sub(r"[\d\.\-]+", "", line).strip(),
                    "qty": int(numbers[-3]),
                    "price": float(numbers[-2]),
                    "amount": float(numbers[-1])
                }
                data["items"].append(item)
            except:
                continue

    return data

def hybrid_ocr_pdf(file_path):
    """
    Hybrid OCR: PyMuPDF text extraction first, fallback to docTR for scanned pages
    """
    if not os.path.exists(file_path):
        print("File not found:", file_path)
        return None

    doc = fitz.open(file_path)
    full_text = ""

    for page in doc:
        # 1️⃣ Try PyMuPDF text extraction
        page_text = page.get_text("text")

        if not page_text.strip():
            # 2️⃣ Fallback to docTR OCR for scanned images
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            result = model([img])
            page_text = result.pages[0].export().get("text", "")

        full_text += page_text + "\n"

    # Extract structured data from combined text
    return extract_data_from_text(full_text)

# -------------------------------
# Example usage
# -------------------------------
if __name__ == "__main__":
    file_path = r"C:\Users\anush\OneDrive\Desktop\OCR\messy_invoice.pdf"  # Replace with your PDF path
    result = hybrid_ocr_pdf(file_path)

    if result:
        print(json.dumps(result, indent=2))
