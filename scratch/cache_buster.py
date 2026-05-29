import os

templates_dir = 'templates'
old_string = "href=\"{{ url_for('static', filename='style.css') }}\""
new_string = "href=\"{{ url_for('static', filename='style.css') }}?v=1.4\""

# Let's also support single quotes just in case
old_string_sq = "href='{{ url_for(\"static\", filename=\"style.css\") }}'"
new_string_sq = "href='{{ url_for(\"static\", filename=\"style.css\") }}?v=1.4'"

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                updated = False
                if old_string in content:
                    content = content.replace(old_string, new_string)
                    updated = True
                if "style.css" in content and "?v=" not in content:
                    # Let's do a more robust replacement if needed
                    content = content.replace("filename='style.css'", "filename='style.css'")
                    # If it has other forms, handle them
                    content = content.replace("href=\"{{ url_for('static', filename='style.css') }}\"", new_string)
                    content = content.replace("href='{{ url_for('static', filename='style.css') }}'", new_string_sq)
                    updated = True
                
                if updated:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Updated cache-buster in {path}")
            except Exception as e:
                print(f"Error processing {path}: {e}")
