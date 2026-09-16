import os

def generate_blueprint():
    target_dirs = ['src/backend', 'src/frontend']
    blueprint_content = "# FieldFlow Automated Progress Blueprint\n\n"
    
    for t_dir in target_dirs:
        if not os.path.exists(t_dir):
            continue
        blueprint_content += f"## Directory: {t_dir}\n\n"
        for file in sorted(os.listdir(t_dir)):
            if file.endswith('.py'):
                file_path = os.path.join(t_dir, file)
                blueprint_content += f"### 📄 {file}\n"
                
                # Extract first 5 lines (usually imports/docstrings) and function names
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    functions = [l.strip() for l in lines if l.strip().startswith('def ')]
                
                blueprint_content += "**Defined Functions/Classes:**\n"
                if functions:
                    for func in functions[:10]: # Limit to top 10 for scannability
                        blueprint_content += f"- `{func}`\n"
                else:
                    blueprint_content += "- *No functions defined yet (Skeletal file)*\n"
                blueprint_content += "\n"
                
    with open('PROJECT_LOG.md', 'w', encoding='utf-8') as log_file:
        log_file.write(blueprint_content)
    print("Success! PROJECT_LOG.md has been automatically updated with your current code state.")

if __name__ == '__main__':
    generate_blueprint()