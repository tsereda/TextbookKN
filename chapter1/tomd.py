import pymupdf4llm
import pathlib
import re

# Convert the document to markdown
md_text = pymupdf4llm.to_markdown("chapter1.pdf", write_images=True)

# Post-processing functions
def fix_superscripts(text):
    return re.sub(r'(\w+)\[(\d+)\]', r'\1<sup>\2</sup>', text)

def fix_missing_f(text):
    return re.sub(r'\bo(?=[^\w\s])', 'of', text)

def fix_formatting(text):
    # Remove extra newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Ensure headers are properly formatted
    text = re.sub(r'^(\*\*[\d\.]+\s+.+?\*\*)$', r'\n\1\n', text, flags=re.MULTILINE)
    
    return text

# Apply post-processing
md_text = fix_superscripts(md_text)
md_text = fix_missing_f(md_text)
md_text = fix_formatting(md_text)

# Write the processed text to a file in UTF-8 encoding
output_path = pathlib.Path("output.md")
output_path.write_text(md_text, encoding='utf-8')

print(f"Processed markdown has been written to {output_path}")