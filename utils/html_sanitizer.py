"""Small allow-list HTML sanitizer for user-authored email templates."""
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

ALLOWED_TAGS = {"a","b","blockquote","br","code","div","em","h1","h2","h3","hr","i","li","ol","p","pre","span","strong","table","tbody","td","th","thead","tr","u","ul"}
VOID_TAGS = {"br", "hr"}
ALLOWED_ATTRS = {"a": {"href", "title"}, "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan"}}

class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.parts=[]; self.suppressed=0
    def handle_starttag(self, tag, attrs):
        tag=tag.lower()
        if tag in {"script","style","iframe","object","svg","math"}: self.suppressed+=1; return
        if self.suppressed or tag not in ALLOWED_TAGS: return
        clean=[]
        for key,value in attrs:
            key=key.lower(); value=value or ""
            if key not in ALLOWED_ATTRS.get(tag,set()): continue
            if key=="href" and urlparse(value).scheme.lower() not in {"","http","https","mailto"}: continue
            clean.append(f' {key}="{escape(value, quote=True)}"')
        self.parts.append(f"<{tag}{''.join(clean)}>")
    def handle_endtag(self, tag):
        tag=tag.lower()
        if tag in {"script","style","iframe","object","svg","math"}:
            self.suppressed=max(0,self.suppressed-1); return
        if not self.suppressed and tag in ALLOWED_TAGS and tag not in VOID_TAGS: self.parts.append(f"</{tag}>")
    def handle_data(self,data):
        if not self.suppressed: self.parts.append(escape(data))

def sanitize_email_html(value):
    parser=_Sanitizer(); parser.feed(value or ""); parser.close(); return "".join(parser.parts)
