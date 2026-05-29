import os

targets = ['contact@processinsight.io', '12 Avenue des Procédés', '75005', 'processinsight.io']
found_any = False

for root, dirs, files in os.walk('.'):
    # Skip temporary or system directories
    if any(p in root for p in ['.git', '__pycache__', '.gemini', 'node_modules', 'scratch']):
        continue
    for file in files:
        if file.endswith(('.html', '.css', '.js', '.py')):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                for t in targets:
                    if t in content:
                        print(f'Found "{t}" in {path}')
                        found_any = True
            except Exception as e:
                pass

if not found_any:
    print("No occurrences of old contact info found.")
