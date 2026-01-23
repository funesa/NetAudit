
import os
import re

static_dir = 'static'
output_file = os.path.join(static_dir, 'style.min.css')

# Order matters for CSS overrides
css_files = [
    'spacing-system.css',
    'style.css',
    'sidebar.css',
    'dashboard.css',
    'clickup-style.css',
    'notifications.css',
    'tables.css',
    'ad_table_modern.css',
    'list-layout.css',
    'premium-modal.css'
]

def minify_css(css):
    # Remove comments
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
    # Remove extra whitespace
    css = re.sub(r'\s+', ' ', css)
    # Remove space around special characters
    css = re.sub(r'\s*([{:;,])\s*', r'\1', css)
    # Remove unnecessary last semicolon in blocks
    css = re.sub(r';}', '}', css)
    return css.strip()

combined_css = ""

for filename in css_files:
    file_path = os.path.join(static_dir, filename)
    if os.path.exists(file_path):
        print(f"Adding {filename}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            combined_css += f"\n/* --- {filename} --- */\n"
            combined_css += content
    else:
        print(f"Warning: {filename} not found.")

minified_css = minify_css(combined_css)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(minified_css)

print(f"Successfully created {output_file}")
print(f"Original size estimate: {len(combined_css)} bytes")
print(f"Minified size: {len(minified_css)} bytes")
