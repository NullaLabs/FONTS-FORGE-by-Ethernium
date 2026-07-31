import base64
from pathlib import Path

root = Path(__file__).resolve().parent.parent
emblem_path = root / "logo_emblem.png"
html_path = root / "presentation_generator.html"

# Read logo and encode to base64
with open(emblem_path, "rb") as f:
    encoded = base64.b64encode(f.read()).decode("utf-8")

data_url = f"data:image/png;base64,{encoded}"

# Read HTML and replace the emblem source
html_content = html_path.read_text(encoding="utf-8")
old_line = "logoImg.src = 'logo_emblem.png';"
new_line = f"logoImg.src = '{data_url}';"

if old_line in html_content:
    html_content = html_content.replace(old_line, new_line)
    html_path.write_text(html_content, encoding="utf-8")
    print("Success: Embedded base64 logo in HTML!")
else:
    print("Error: Could not find target line in HTML.")
