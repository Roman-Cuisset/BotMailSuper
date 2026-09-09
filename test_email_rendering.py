import sys
import os
from utils.email_sender import render_email_html

def test_rendering():
    print("Testing email rendering...")
    
    # Test Data
    sender = "Test User"
    message = "Hello,\nThis is a test message.\n\nWith multiple lines."
    attachments = [("photo1.jpg", b""), ("document.pdf", b""), ("image.png", b"")]
    
    # Render
    html = render_email_html(sender, message, attachments, is_vip=False)
    
    # Verify Newlines
    if "<br>" in html and "Hello,<br>This is a test message.<br><br>With multiple lines." in html:
        print("✅ Newline conversion passed.")
    else:
        print("❌ Newline conversion failed.")
        print(f"Snippet: {html[html.find('Hello'):html.find('lines.')+6]}")

    # Verify Attachments Layout (CSS check)
    # We check if the CSS file content is correct, or if the HTML structure is correct.
    # Since render_email_html reads the file, we can check if the generated HTML contains the new CSS classes if they were inline,
    # but here the CSS is in the <head>. The render function reads the whole file.
    
    if "flex-direction: row" in html:
        print("✅ CSS 'flex-direction: row' found.")
    else:
        print("❌ CSS 'flex-direction: row' NOT found.")

    if "display: inline-block" in html:
        print("✅ CSS 'display: inline-block' found for li.")
    else:
        print("❌ CSS 'display: inline-block' NOT found.")

    print("✅ Rendering checks completed without creating runtime files.")

if __name__ == "__main__":
    test_rendering()
