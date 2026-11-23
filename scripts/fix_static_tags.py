import os, re
proj_root = r"c:/Ericka Fatima/College (S.Y. 2024-2028)/Cebu Institute of Technology- University/3rd Year (S.Y. 2026-2027)/1st Semester/Information Management 2 (CSIT327)/Projects/tapick/tapick"
template_dir = os.path.join(proj_root, 'templates')
for root, dirs, files in os.walk(template_dir):
    for f in files:
        if f.endswith('.html'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as fh:
                content = fh.read()
            # fix link tags
            content = re.sub(r"href=['\"]\{\{\% static '([^']+)'\%\}\}['\"]", r'href="{% static "\1" %}"', content)
            # fix script tags
            content = re.sub(r"src=['\"]\{\{\% static '([^']+)'\%\}\}['\"]", r'src="{% static "\1" %}"', content)
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(content)
print('Fixed template tag syntax')
