from playwright.sync_api import sync_playwright
import time
import os

def download_pdf_from_url(url, save_dir="downloads"):
    """
    Uses Playwright to navigate to a URL and download the PDF.
    Handles 403 Forbidden by mimicking a real browser.
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    filename = url.split('/')[-1]
    if not filename.endswith('.pdf'):
        filename = "downloaded_file.pdf"
    
    save_path = os.path.join(save_dir, filename)
    
    print(f"Attempting to download from: {url}")
    
    with sync_playwright() as p:
        # Launch browser (headless=True for production, False for debugging)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # Navigate to the URL
            # Note: For direct PDF links, Playwright might not 'render' the page but trigger a download
            # We need to handle both cases: rendered PDF or attachment download
            
            response = page.goto(url, wait_until="networkidle")
            
            if response.status == 403:
                print("Error: 403 Forbidden even with browser. Trying to wait...")
                time.sleep(2)
            
            # Check if it's a PDF content type
            content_type = response.headers.get('content-type', '')
            
            if 'application/pdf' in content_type:
                print("Direct PDF content detected. Saving...")
                body = response.body()
                with open(save_path, 'wb') as f:
                    f.write(body)
                print(f"Saved to {save_path}")
                return save_path
            else:
                print(f"Content type is {content_type}. Might not be a direct PDF link.")
                # Fallback: Take a screenshot if it's not a PDF (for debugging)
                # page.screenshot(path="debug_screenshot.png")
                return None
                
        except Exception as e:
            print(f"Error downloading PDF: {e}")
            return None
        finally:
            browser.close()

    return None
