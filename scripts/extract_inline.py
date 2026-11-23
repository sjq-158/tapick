import os, re, pathlib, sys

# Dynamically determine the project root based on this script's location
proj_root = pathlib.Path(__file__).resolve().parents[1]


template_dir = os.path.join(proj_root, "templates")
static_css_dir = os.path.join(proj_root, "static", "css")
static_js_dir = os.path.join(proj_root, "static", "js")
os.makedirs(static_css_dir, exist_ok=True)
os.makedirs(static_js_dir, exist_ok=True)

html_files = []
for root, dirs, files in os.walk(template_dir):
    for f in files:
        if f.endswith('.html'):
            html_files.append(os.path.join(root, f))

for html_path in html_files:
    rel = os.path.relpath(html_path, template_dir)
    base_name = os.path.splitext(rel.replace(os.sep, '_'))[0]
    with open(html_path, 'r', encoding='utf-8') as fh:
        content = fh.read()
    # extract <style> blocks
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', content, flags=re.DOTALL|re.IGNORECASE)
    if style_blocks:
        css_content = "\n\n".join(block.strip() for block in style_blocks if block.strip())
        css_path = os.path.join(static_css_dir, f"{base_name}.css")
        with open(css_path, 'w', encoding='utf-8') as fcss:
            fcss.write(css_content)
        # replace all style blocks with link tag
        content = re.sub(r'<style[^>]*>.*?</style>', f"<link rel='stylesheet' href='{{% static 'css/{base_name}.css' %}}'>", content, flags=re.DOTALL|re.IGNORECASE)
    # extract inline <script> without src
    script_blocks = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', content, flags=re.DOTALL|re.IGNORECASE)
    if script_blocks:
        js_content = "\n\n".join(block.strip() for block in script_blocks if block.strip())
        js_path = os.path.join(static_js_dir, f"{base_name}.js")
        with open(js_path, 'w', encoding='utf-8') as fjs:
            fjs.write(js_content)
        # remove inline script blocks
        content = re.sub(r'<script(?![^>]*src)[^>]*>.*?</script>', '', content, flags=re.DOTALL|re.IGNORECASE)
        # insert script tag before </body>
        insert_tag = f"<script src='{{% static 'js/{base_name}.js' %}}'></script>"
        content = re.sub(r'(</body>)', insert_tag + r"\1", content, flags=re.IGNORECASE)
    # write back modified html
    with open(html_path, 'w', encoding='utf-8') as fh:
        fh.write(content)
print('Processed', len(html_files), 'HTML files')
