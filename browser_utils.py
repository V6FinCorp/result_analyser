from playwright.sync_api import sync_playwright
import time
import os

def download_pdf_from_url(url, save_dir="downloads"):
    """
    Uses Playwright to navigate to a URL and download the PDF.
    Handles both direct PDF links and download-triggered PDFs.
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    filename = url.split('/')[-1].split('?')[0]  # Remove query params
    if not filename.endswith('.pdf'):
        filename = "downloaded_file.pdf"
    
    save_path = os.path.join(save_dir, filename)
    
    print(f"Attempting to download from: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            accept_downloads=True
        )
        page = context.new_page()
        
        try:
            # Try Method 1: Expect download and navigate
            try:
                with page.expect_download(timeout=30000) as download_info:
                    page.goto(url, wait_until="commit")
                
                download = download_info.value
                print("Download triggered. Saving...")
                download.save_as(save_path)
                print(f"Saved to {save_path}")
                return save_path
                
            except Exception as download_error:
                # Method 2: If download didn't trigger, try to get PDF content from response
                print(f"Download method failed: {download_error}")
                print("Trying direct content fetch...")
                
                try:
                    response = page.goto(url, wait_until="load", timeout=30000)
                    
                    if response and response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        
                        if 'application/pdf' in content_type:
                            print("Direct PDF content detected. Saving...")
                            body = response.body()
                            with open(save_path, 'wb') as f:
                                f.write(body)
                            print(f"Saved to {save_path}")
                            return save_path
                        else:
                            print(f"Content type is {content_type}. Not a PDF.")
                            return None
                    elif response and response.status == 403:
                        print("Error: 403 Forbidden")
                        return None
                    else:
                        print(f"Unexpected response status: {response.status if response else 'None'}")
                        return None
                except Exception as content_error:
                    print(f"Content fetch also failed: {content_error}")
                    return None
                
        except Exception as e:
            print(f"Error downloading PDF: {e}")
            return None
        finally:
            browser.close()

    return None
