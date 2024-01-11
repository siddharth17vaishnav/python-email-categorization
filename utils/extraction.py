import fitz
import base64
import io
from PIL import Image
from pytesseract import pytesseract
from bs4 import BeautifulSoup
import re


def extract_text_from_pdf(pdf_content):
    pdf_content = pdf_content.replace('-', '+').replace('_', '/')
    padded_data = pdf_content + '=' * ((4 - len(pdf_content) % 4) % 4)
    attachment_data_base64 = base64.urlsafe_b64decode(padded_data)
    pdf_document = fitz.open(stream=attachment_data_base64, filetype="pdf")
    text = ""
    for page_number in range(pdf_document.page_count):
        page = pdf_document[page_number]
        text += page.get_text()
    cleaned_text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text


def extract_text_from_image(image_content):
    try:
        image_data = base64.urlsafe_b64decode(image_content)
        image_stream = io.BytesIO(image_data)
        image = Image.open(image_stream)
        text = pytesseract.image_to_string(image)
        cleaned_text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        return cleaned_text
    except Exception as e:
        print(f"Error performing OCR: {str(e)}")
        return None


def extract_links_from_html_part(html_part):
    soup = BeautifulSoup(html_part, 'html.parser')
    anchor_tags = soup.find_all('a', href=True)
    links = []
    for anchor_tag in anchor_tags:
        link_url = anchor_tag['href']
        links.append(link_url)
    return list(filter(lambda item: "http" in item, links))


def extract_logo_from_html(html_content, min_width=10):
    soup = BeautifulSoup(html_content, 'html.parser')
    main_logo_tag = soup.find('img', {'width': lambda x: x and int(x) > min_width})
    if main_logo_tag:
        main_logo_src = main_logo_tag.get('src')
        return main_logo_src
    else:
        return None


def extract_activation_link(links):
    activation_keywords = ["activate", "verify", "confirmation", "activation","auth"]
    activation_link_candidates = []
    for link in links:
        if any(keyword in link.lower() for keyword in activation_keywords):
            activation_link_candidates.append(link)

    return activation_link_candidates


def get_html_content_from_message(message):
        payload = message.get("payload", {})
        parts = payload.get("parts", [])
        html_part = next((part for part in parts if part.get("mimeType", "") == "text/html"), {})
        body = html_part.get("body", {})
        data = body.get("data", "")
        html_content = base64.urlsafe_b64decode(data).decode('utf-8')
        return html_content

