"""
HTML Email Templates - Phase 4
Converts Markdown to HTML for rich email formatting
"""
import markdown
import re

def markdown_to_html(text):
    """Convert Markdown text to HTML"""
    # Convert markdown to HTML
    html = markdown.markdown(text, extensions=['extra', 'nl2br'])
    
    # Wrap in email template
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1, h2, h3 {{ color: #0d6efd; }}
            a {{ color: #0d6efd; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            code {{
                background: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: monospace;
            }}
            pre {{
                background: #f4f4f4;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
            }}
            blockquote {{
                border-left: 4px solid #0d6efd;
                padding-left: 15px;
                margin-left: 0;
                color: #666;
            }}
            ul, ol {{ padding-left: 20px; }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """

def get_template(template_name, **kwargs):
    """Get predefined HTML template"""
    templates = {
        'business': """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                    <td align="center" style="padding: 40px 20px;">
                        <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; background: white; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.1); overflow: hidden;">
                            <!-- Header with gradient -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #7e8ba3 100%); padding: 40px 30px; text-align: center;">
                                    <div style="width: 60px; height: 60px; background: rgba(255,255,255,0.2); border-radius: 12px; margin: 0 auto 20px; display: inline-flex; align-items: center; justify-content: center; backdrop-filter: blur(10px);">
                                        <span style="font-size: 32px; color: white;">💼</span>
                                    </div>
                                    <h1 style="margin: 0; color: white; font-size: 28px; font-weight: 600; letter-spacing: -0.5px;">{title}</h1>
                                    <div style="width: 60px; height: 3px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.8), transparent); margin: 20px auto 0;"></div>
                                </td>
                            </tr>
                            
                            <!-- Content area -->
                            <tr>
                                <td style="padding: 40px 35px; background: white;">
                                    <div style="color: #2d3748; font-size: 16px; line-height: 1.8; white-space: pre-wrap;">
                                        {content}
                                    </div>
                                </td>
                            </tr>
                            
                            <!-- Accent line -->
                            <tr>
                                <td style="background: linear-gradient(90deg, #1e3c72, #2a5298, #7e8ba3); height: 4px;"></td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="background: #f8fafc; padding: 30px 35px; text-align: center; border-top: 1px solid #e2e8f0;">
                                    <p style="margin: 0; color: #64748b; font-size: 13px; line-height: 1.6;">
                                        {footer}
                                    </p>
                                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e2e8f0;">
                                        <p style="margin: 0; color: #94a3b8; font-size: 11px;">
                                            🔒 Confidential Business Communication
                                        </p>
                                    </div>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """,
        
        'casual': """
        <div style="font-family: 'Comic Sans MS', cursive; max-width: 600px; margin: 0 auto; background: #fff3cd; padding: 20px; border-radius: 10px;">
            <h2 style="color: #856404;">{title}</h2>
            <div style="color: #333;">
                {content}
            </div>
            <p style="margin-top: 30px; color: #856404; font-style: italic;">{footer}</p>
        </div>
        """,
        
        'minimal': """
        <div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h3 style="border-bottom: 2px solid #333; padding-bottom: 10px;">{title}</h3>
            <div style="margin: 20px 0;">
                {content}
            </div>
            <p style="color: #666; font-size: 14px; margin-top: 30px;">{footer}</p>
        </div>
        """,
        
        'newsletter': """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: white;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 20px; text-align: center;">
                <h1 style="margin: 0; font-size: 32px;">{title}</h1>
            </div>
            <div style="padding: 30px;">
                {content}
            </div>
            <div style="background: #f8f9fa; padding: 20px; text-align: center; border-top: 3px solid #667eea;">
                <p style="color: #666; margin: 0;">{footer}</p>
            </div>
        </div>
        """
    }
    
    template = templates.get(template_name, templates['minimal'])
    return template.format(**kwargs)

def apply_template(text, template_name='minimal', title='', footer=''):
    """Apply HTML template to text"""
    # Convert markdown to HTML
    content_html = markdown.markdown(text, extensions=['extra', 'nl2br'])
    
    # Apply template
    return get_template(
        template_name,
        title=title or 'Message',
        content=content_html,
        footer=footer or 'Sent via Bot Mail Super'
    )

def is_html(text):
    """Check if text contains HTML"""
    return bool(re.search(r'<[^>]+>', text))
