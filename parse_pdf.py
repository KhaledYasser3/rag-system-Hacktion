import os
import pdfplumber

def parse_guidelines_pdf(pdf_path):
    """
    Parses a PDF document page-by-page, extracting text and tracking page numbers.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: The file {pdf_path} was not found.")
        return None

    parsed_pages = []

    print(f"Opening PDF file: {pdf_path}...")
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Successfully opened! Total pages: {total_pages}")

        # Let's extract the first few pages as a test
        # We start from 1-indexed page number for natural citation
        for page in pdf.pages:
            page_num = page.page_number
            text = page.extract_text()
            
            # Store the extracted text and metadata
            if text:
                parsed_pages.append({
                    "page_number": page_num,
                    "text": text,
                    "char_count": len(text)
                })
            
            # Print progress for every 10 pages
            if page_num % 10 == 0 or page_num == total_pages:
                print(f"Parsed {page_num}/{total_pages} pages...")

    return parsed_pages

if __name__ == "__main__":
    pdf_filename = "9789241550284-eng.pdf"
    
    pages_data = parse_guidelines_pdf(pdf_filename)
    
    if pages_data:
        print("\n--- Summary of Parsed Document ---")
        print(f"Total pages with text: {len(pages_data)}")
        
        # Display a sample from page 12 (where guidelines often begin after intro)
        sample_page = None
        for p in pages_data:
            if p["page_number"] == 12:
                sample_page = p
                break
        
        if not sample_page:
            sample_page = pages_data[0]
            
        print(f"\n--- Sample Text from Page {sample_page['page_number']} ---")
        # Print the first 500 characters of the sample page
        print(sample_page['text'][:500] + "...\n")
