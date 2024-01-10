import fitz
import base64
import io
from PIL import Image
from pytesseract import pytesseract


def extract_text_from_pdf(pdf_content):
    pdf_content = pdf_content.replace('-', '+').replace('_', '/')
    padded_data = pdf_content + '=' * ((4 - len(pdf_content) % 4) % 4)
    attachment_data_base64 = base64.urlsafe_b64decode(padded_data)
    pdf_document = fitz.open(stream=attachment_data_base64, filetype="pdf")
    text = ""
    for page_number in range(pdf_document.page_count):
        page = pdf_document[page_number]
        text += page.get_text()
    return text


def extract_text_from_image(image_content):
    try:
        image_data = base64.urlsafe_b64decode(image_content)
        image_stream = io.BytesIO(image_data)
        image = Image.open(image_stream)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error performing OCR: {str(e)}")
        return None
