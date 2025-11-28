import logging
from playwright.sync_api import sync_playwright
import time
import os

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_pdf_from_url(url, save_dir="downloads"):
    """
    Uses Playwright to navigate to a URL and download the PDF.
    Handles 403 Forbidden by mimicking a real browser.
    Supports both direct PDF rendering and attachment downloads.
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    filename = url.split('/')[-1]
    if not filename.endswith('.pdf'):
        filename = "downloaded_file.pdf"
    
    save_path = os.path.join(save_dir, filename)
    
    logger.info(f"Attempting to download from: {url}")
    
    with sync_playwright() as p:
        # Launch browser (headless=True for production)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            accept_downloads=True
        )
        page = context.new_page()
        
        try:
            # Setup download listener
            with page.expect_download(timeout=10000) as download_info:
                try:
                    # Navigate to the URL
                    response = page.goto(url, wait_until="networkidle", timeout=15000)
                    
                    if response.status == 403:
                        logger.warning("Error: 403 Forbidden. Trying to wait...")
                        time.sleep(2)
                    
                    # Check if it's a direct PDF content type
                    content_type = response.headers.get('content-type', '')
                    if 'application/pdf' in content_type:
                        logger.info("Direct PDF content detected. Saving...")
                        body = response.body()
                        with open(save_path, 'wb') as f:
                            f.write(body)
                        logger.info(f"Saved to {save_path}")
                        return save_path
                        
                except Exception as nav_err:
                    # Navigation might fail if it triggers a download immediately, which is fine
                    logger.info(f"Navigation finished (possibly triggered download): {nav_err}")

            # If we are here, a download event might have been triggered
            download = download_info.value
            logger.info(f"Download event detected. Saving to {save_path}")
            download.save_as(save_path)
            return save_path
                
        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            # Fallback: Check if file exists anyway (sometimes race conditions)
            if os.path.exists(save_path):
                return save_path
            return None
        finally:
            browser.close()

    return None
