import os
import time
import subprocess
import shutil
import sys

# --- PATH CONFIGURATION ---
# Dynamically resolves paths assuming standard Next.js / FastAPI folder structure
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PROD = os.path.join(BACKEND_DIR, "env_prod")

# Pushes the React code straight into a new Next.js route: localhost:3000/erp
FRONTEND_TARGET = os.path.join(os.path.dirname(BACKEND_DIR), "frontend", "src", "app", "erp")

os.makedirs(ENV_PROD, exist_ok=True)
os.makedirs(FRONTEND_TARGET, exist_ok=True)

print("🚀 [PROD GATEWAY] Active. Listening for AI Deployments in env_prod...")

active_api_process = None
known_files = set(os.listdir(ENV_PROD))

while True:
    try:
        current_files = set(os.listdir(ENV_PROD))
        new_files = current_files - known_files
        
        for file in new_files:
            filepath = os.path.join(ENV_PROD, file)
            print(f"\n📦 [PROD GATEWAY] Approved deployment detected: {file}")
            
            # --- BACKEND DEPLOYMENT LOGIC ---
            if file.endswith('.py'):
                # 1. Kill the old version of the API if it's running
                if active_api_process:
                    print("🛑 [PROD GATEWAY] Terminating previous API version...")
                    active_api_process.terminate()
                    active_api_process.wait()
                
                # 2. Port Binding Injection (Self-Healing)
                # The AI often hardcodes port 8000, which conflicts with your main.py Dashboard bridge.
                # We intercept the code and force it to run on port 8001 for Production.
                with open(filepath, 'r', encoding='utf-8') as f:
                    code = f.read()
                if 'port=8000' in code:
                    code = code.replace('port=8000', 'port=8001')
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(code)

                # 3. Boot the new live API
                print(f"🟢 [PROD GATEWAY] Booting Live API: {file} on Port 8001...")
                active_api_process = subprocess.Popen([sys.executable, filepath])
                
            # --- FRONTEND DEPLOYMENT LOGIC ---
            elif file.endswith('.tsx'):
                print(f"⚛️ [PROD GATEWAY] Injecting React component to Next.js App Router...")
                # Next.js App Router requires the file to be named page.tsx to create a route
                target_file = os.path.join(FRONTEND_TARGET, "page.tsx")
                shutil.copy(filepath, target_file)
                print(f"✨ [PROD GATEWAY] Frontend is LIVE at http://localhost:3000/erp")

        known_files = current_files
    except Exception as e:
        print(f"⚠️ Gateway Error: {str(e)}")
        
    # Poll the directory every 2 seconds
    time.sleep(2)