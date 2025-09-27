import os
import subprocess
import sys
import time
import re
import ast
from mistralai import Mistral

# 🔧 Configuration
MISTRAL_API_KEY = "1QJOIuK9SIhpKkF9vwg3IMgMIiEr0fQR"
APP_FILE = "app.py"
REQUIREMENTS_FILE = "requirements.txt"
VENV_DIR = "venv"
MAX_RETRIES = 5

client = Mistral(api_key=MISTRAL_API_KEY)

# === AI with STRICT code-only enforcement ===
def ask_for_code(prompt: str) -> str:
    """Ask AI for PURE CODE ONLY — no explanations."""
    system_prompt = (
        "You are a code generator. Output ONLY valid Python code. "
        "NEVER include explanations, markdown, or natural language. "
        "Start directly with 'from' or 'import'."
    )
    try:
        resp = client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return ""

# === Advanced Code Cleaning ===
def extract_code_block(text: str) -> str:
    """Extract code from markdown or natural language."""
    # Try to find a Python code block
    match = re.search(r"```(?:python|py)?\s*\n(.*?)\n```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # If no block, assume entire text is code (but remove common prefixes)
    lines = text.strip().splitlines()
    cleaned = []
    for line in lines:
        if re.match(r"^(Here is|Below is|Sure|I have|The code is|```)", line, re.IGNORECASE):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()

# === Validate Code Safety ===
def is_syntax_valid(code: str) -> bool:
    """Check if code is syntactically valid Python."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False

def is_fullstack_valid(code: str) -> bool:
    """Check if code is a valid full-stack FastAPI app."""
    if not is_syntax_valid(code):
        return False
    return (
        "FastAPI" in code 
        and "uvicorn.run" in code
        and ("@app.get" in code or "HTMLResponse" in code)
    )

# === Generate Initial App ===
def generate_initial_app(idea: str) -> str:
    prompt = f"""
Generate a single-file FastAPI app for: "{idea}"

Requirements:
- Use FastAPI, Bootstrap 5 (CDN), JavaScript, AJAX (fetch)
- Embed HTML in Python string
- Include at least one POST endpoint
- MUST end with:

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

Output ONLY Python code. No text before or after.
"""
    for _ in range(3):
        raw = ask_for_code(prompt)
        code = extract_code_block(raw)
        if is_fullstack_valid(code):
            return code
        time.sleep(1)
    
    # Fallback: minimal working app
    return f'''from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>{idea or 'Education Site'}</title>
    <meta charset="utf-8">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="container">
    <h1 class="mt-4">Welcome to {idea or 'Our Education Platform'}</h1>
    <div class="alert alert-success">✅ Server running on http://localhost:8000</div>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

# === Capture Full Error Traceback ===
def capture_full_error(python_exe: str, timeout: int = 10) -> str:
    """Run app briefly and capture full error if it crashes."""
    try:
        proc = subprocess.Popen(
            [python_exe, APP_FILE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
        
        # Return stderr (where tracebacks appear)
        return stderr.strip() or stdout.strip()
    except Exception as e:
        return str(e)

# === Project Setup ===
def setup_project():
    # requirements.txt
    with open(REQUIREMENTS_FILE, "w") as f:
        f.write("fastapi\nuvicorn[standard]\n")
    
    # venv
    if not os.path.exists(VENV_DIR):
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
    
    python_exe = os.path.join(VENV_DIR, "Scripts", "python.exe") if os.name == "nt" else os.path.join(VENV_DIR, "bin", "python")
    subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([python_exe, "-m", "pip", "install", "-r", REQUIREMENTS_FILE], check=True)
    
    # Launcher
    if os.name == "nt":
        with open("run_app.bat", "w") as f:
            f.write(f'''@echo off
cd /d "{os.path.abspath(".")}
"{python_exe}" "{APP_FILE}"
if %ERRORLEVEL% NEQ 0 (
    echo *** Crashed ***
    pause
)
''')
    return python_exe

# === Intelligent Fix Agent ===
def fix_with_context(idea: str, error_log: str) -> str:
    # Extract meaningful error (last 20 lines)
    error_lines = error_log.splitlines()
    meaningful_error = "\n".join([line for line in error_lines if line.strip()][-20:])
    
    prompt = f"""
Fix this FastAPI app. The error is:

{meaningful_error}

Original idea: "{idea}"

Rules:
- Output ONLY Python code
- Keep the same structure: FastAPI + embedded HTML + AJAX
- MUST include uvicorn.run block
- Do not add explanations
"""
    for _ in range(2):
        raw = ask_for_code(prompt)
        code = extract_code_block(raw)
        if is_fullstack_valid(code):
            return code
        time.sleep(1)
    return generate_initial_app(idea)  # fallback

# === Main Agent Loop ===
def main():
    idea = input("💡 Describe your app: ").strip() or "education website"
    
    print("⚡ Generating app...")
    code = generate_initial_app(idea)
    with open(APP_FILE, "w", encoding="utf-8") as f:
        f.write(code)
    
    python_exe = setup_project()
    print("✅ Project setup complete")

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🔁 Attempt {attempt}/{MAX_RETRIES}")
        
        # Test if app starts without crashing
        error_output = capture_full_error(python_exe, timeout=8)
        
        if not error_output or "Uvicorn running on" in error_output:
            print("\n🎉 SUCCESS! App is running on http://localhost:8000")
            # Keep it running
            subprocess.run([python_exe, APP_FILE])
            return
        
        print(f"\n🛠️ Error detected. Applying intelligent fix...")
        code = fix_with_context(idea, error_output)
        with open(APP_FILE, "w", encoding="utf-8") as f:
            f.write(code)
        time.sleep(2)
    
    print(f"\n⚠️ Max retries reached. Final error:\n{error_output[:500]}")

if __name__ == "__main__":
    main()