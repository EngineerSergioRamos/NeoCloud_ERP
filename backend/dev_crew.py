import os
import requests
import time
import subprocess
import shutil
import PyPDF2
from typing import Any, Optional
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()

# --- 1. SDLC ENVIRONMENT CONFIGURATION ---
CONTEXT_DIR = r"C:\Users\Sergio Ramos\Documents\LMStudioAgents\LocalAI\LocalAI\NeoCloud_ERP\devcontext"
ENV_DEV = os.path.join(os.getcwd(), "env_dev")
ENV_SIT = os.path.join(os.getcwd(), "env_sit")
ENV_PROD = os.path.join(os.getcwd(), "env_prod")

for d in [CONTEXT_DIR, ENV_DEV, ENV_SIT, ENV_PROD]:
    os.makedirs(d, exist_ok=True)

def broadcast_to_ui(message: str):
    try:
        requests.post("http://localhost:8000/broadcast-agent", json={"payload": message})
    except:
        pass

def agent_step_stream(step_output):
    broadcast_to_ui("🧠 AI is processing context and formulating next steps...")

# --- 2. TOOLS ---
@tool("list_context_files")
def list_context_files(query: Any = None) -> str:
    """Lists all documentation files in the devcontext folder."""
    broadcast_to_ui("📂 ACTION: Scanning devcontext directory...")
    try:
        files = os.listdir(CONTEXT_DIR)
        return "Available Context Files:\n" + "\n".join(files) if files else "Folder empty."
    except Exception as e:
        return f"ERROR: {str(e)}"

@tool("read_context_file")
def read_context_file(filename: str) -> str:
    """Reads project documents. Handles .txt and .pdf safely."""
    broadcast_to_ui(f"📖 ACTION: Reading context file -> {filename}")
    filepath = os.path.join(CONTEXT_DIR, filename)
    try:
        if filename.lower().endswith('.pdf'):
            text_content = []
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text_content.append(page.extract_text())
            return "\n".join(text_content)
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        return f"ERROR reading {filename}: {str(e)}"

@tool("write_dev_code")
def write_dev_code(filename: str, content: str) -> str:
    """Writes code to the Development Environment (env_dev)."""
    broadcast_to_ui(f"💻 ACTION: Writing code to -> {filename}")
    filepath = os.path.join(ENV_DEV, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"SUCCESS: Saved {filename}. Proceed to your next logical step."
    except Exception as e:
        return f"ERROR writing file: {str(e)}"

@tool("read_dev_code")
def read_dev_code(filename: str) -> str:
    """Reads code from the Development Environment."""
    filepath = os.path.join(ENV_DEV, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"ERROR reading file: {str(e)}"

@tool("execute_python_test")
def execute_python_test(test_filename: str, test_code: str, test_run_number: int) -> str:
    """Saves a test to env_sit, runs it, and returns a clean error log if it fails. MUST use test_run_number."""
    broadcast_to_ui(f"⚙️ ACTION: Executing integration test (Run #{test_run_number}) -> {test_filename}")
    
    if "import pytest" in test_code or "import unittest" in test_code:
        broadcast_to_ui("⚠️ WARNING: Agent tried to use pytest. Forcing raw Python assertions...")
        return "TEST REJECTED: DO NOT use pytest or unittest. Write a raw Python script using standard 'assert' statements and print('Success'). Try again with a new test_run_number."

    filepath = os.path.join(ENV_SIT, test_filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(test_code)
        
        env_vars = os.environ.copy()
        env_vars["PYTHONPATH"] = ENV_DEV
        
        result = subprocess.run(["python", filepath], capture_output=True, text=True, timeout=15, env=env_vars)
        
        if result.returncode == 0:
            broadcast_to_ui("✅ TEST PASSED: No errors detected in code.")
            return "TEST PASSED SUCCESSFULLY. You must now use 'send_pr_to_dashboard'."
        else:
            broadcast_to_ui("❌ TEST FAILED: Traceback generated. AI initiating self-healing...")
            error_log = result.stderr[-800:] if result.stderr else result.stdout[-800:]
            return (
                f"TEST FAILED! Read this error:\n{error_log}\n\n"
                "CRITICAL RECOVERY: 1. Use 'write_dev_code' to fix the bug.\n"
                "2. When writing code, ensure 'content' is a SINGLE valid JSON string. DO NOT use triple quotes.\n"
                "3. Increase 'test_run_number' so the system does not block your input as a duplicate."
            )
    except Exception as e:
        return f"EXECUTION CRASH: {str(e)[:200]}"

@tool("send_pr_to_dashboard")
def send_pr_to_dashboard(pull_request_markdown: str) -> str:
    """Transmits the code review to the UI."""
    broadcast_to_ui("🚀 ACTION: Pushing Pull Request to Senior Engineer Dashboard.")
    try:
        requests.post("http://localhost:8000/show-proposal", json={"plan": pull_request_markdown})
        return "SUCCESS: PR sent to UI. Your job is done. Output 'Final Answer: QA_DONE' immediately."
    except:
        return "ERROR: Bridge offline."

@tool("wait_for_engineering_director")
def wait_for_engineering_director(query: Any = None) -> str:
    """Polls the dashboard for the human Director's approval."""
    broadcast_to_ui("⏳ WAITING: Paused for Senior Engineer Manual Approval...")
    while True:
        try:
            response = requests.get("http://localhost:8000/check-approval-status")
            data = response.json()
            if data.get("approved"):
                feedback = data.get('feedback')
                broadcast_to_ui(f"🔓 APPROVED: Feedback received -> {feedback}")
                # Clean natural return instead of an Exception
                return f"APPROVAL RECEIVED. Feedback: {feedback}. You MUST now use 'deploy_to_production' to deploy the files."
        except: pass
        time.sleep(2)

@tool("deploy_to_production")
def deploy_to_production(filename: str) -> str:
    """Promotes a file from env_dev to env_prod after approval."""
    broadcast_to_ui(f"📦 ACTION: Deploying {filename} to PRODUCTION env.")
    src = os.path.join(ENV_DEV, filename)
    dst = os.path.join(ENV_PROD, filename)
    try:
        shutil.copy(src, dst)
        return f"SUCCESS: {filename} is live in PRODUCTION."
    except Exception as e:
        return f"DEPLOYMENT ERROR: {str(e)}"

# --- 3. CONFIGURATION ---
local_llm = LLM(
    model="openai/zai-org/glm-4.6v-flash",
    base_url="http://192.168.1.90:1234/v1",
    api_key="lm-studio",
    temperature=0.1, 
    max_tokens=3000,
    stop=["Observation:", "\nObservation:"]
)

strict_format = (
    "\n\nCRITICAL SYSTEM RULE: You must follow the ReAct format strictly.\n"
    "Thought: [your reasoning]\n"
    "Action: [exact tool name]\n"
    "Action Input: {\"arg\": \"value\"}\n\n"
    "JSON ESCAPING RULE: When using write_dev_code, the 'content' MUST be a single string. DO NOT use triple quotes for docstrings, as they break the JSON parser. Keep code simple and use standard '#' for comments.\n"
    "If the system says 'I tried reusing the same input', YOU MUST change your Action Input slightly (e.g. increase test_run_number) and try again.\n"
    "When your goal is fully complete, you MUST output exactly your assigned Final Answer string."
)

# --- 4. AGENTS ---
backend_lead = Agent(
    role='Principal Backend Engineer',
    goal='Architect FastAPI logic in env_dev based on devcontext.',
    backstory='You are a senior engineer. Write clean code without using python docstrings (triple quotes).' + strict_format,
    llm=local_llm,
    tools=[list_context_files, read_context_file, write_dev_code, read_dev_code],
    verbose=True,
    max_iter=10,
    step_callback=agent_step_stream
)

frontend_architect = Agent(
    role='Senior Frontend Architect',
    goal='Build React/Next.js UIs in env_dev aligned with context.',
    backstory='You are a senior frontend developer. Do not use triple quotes in your code.' + strict_format,
    llm=local_llm,
    tools=[list_context_files, read_context_file, write_dev_code, read_dev_code],
    verbose=True,
    max_iter=10,
    step_callback=agent_step_stream
)

qa_lead = Agent(
    role='Principal QA Engineer',
    goal='Test the backend code. If tests fail, rewrite the dev code to fix bugs. Once passing, send PR and exit.',
    backstory='You test code. You MUST pass a new test_run_number integer each time you test. Do not use triple quotes when fixing code.' + strict_format,
    llm=local_llm,
    tools=[read_dev_code, write_dev_code, execute_python_test, send_pr_to_dashboard],
    verbose=True,
    max_iter=15,
    step_callback=agent_step_stream
)

devops_manager = Agent(
    role='Release Manager',
    goal='Wait for Director approval, then deploy approved files to Production and exit.',
    backstory='You deploy code safely, but ONLY after getting human approval.' + strict_format,
    llm=local_llm,
    tools=[wait_for_engineering_director, deploy_to_production],
    verbose=True,
    max_iter=5,
    step_callback=agent_step_stream
)

# --- 5. TASKS ---
task_backend = Task(
    description="Read requirements.txt and create 'fasar_calc.py' in env_dev. DO NOT use triple-quotes for docstrings.",
    expected_output="BACKEND_DONE",
    agent=backend_lead
)

task_frontend = Task(
    description="Read requirements.txt and create 'Dashboard.tsx' in env_dev.",
    expected_output="FRONTEND_DONE",
    agent=frontend_architect
)

task_qa = Task(
    description="""
    1. Read 'fasar_calc.py'.
    2. Use 'execute_python_test' to test it. (Use test_run_number: 1). Write short, simple code.
    3. If it fails, fix the source code using 'write_dev_code'.
    4. Re-run 'execute_python_test'. (CRITICAL: You MUST use test_run_number: 2, then 3, etc.)
    5. Once passing, use 'send_pr_to_dashboard'.
    6. IMMEDIATELY AFTER sending the PR, output 'Final Answer: QA_DONE'. DO NOT DO ANYTHING ELSE.
    """,
    expected_output="QA_DONE",
    agent=qa_lead
)

task_deploy = Task(
    description="""
    1. Use 'wait_for_engineering_director' to check if the PR is approved.
    2. Once approved, use 'deploy_to_production' to move 'fasar_calc.py' to env_prod.
    3. Use 'deploy_to_production' to move 'Dashboard.tsx' to env_prod.
    4. Output 'Final Answer: DEPLOY_DONE'.
    """,
    expected_output="DEPLOY_DONE",
    agent=devops_manager
)

def run_sdlc():
    dev_crew = Crew(
        agents=[backend_lead, frontend_architect, qa_lead, devops_manager],
        tasks=[task_backend, task_frontend, task_qa, task_deploy],
        process=Process.sequential,
        verbose=True,
        cache=False
    )
    dev_crew.kickoff()

if __name__ == "__main__":
    broadcast_to_ui("🟢 [SYSTEM] Booting Multi-Environment SDLC Cluster...")
    run_sdlc()
    broadcast_to_ui("🏁 [SYSTEM] SDLC Sprint Successfully Concluded.")