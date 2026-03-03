import os
import redis
import requests
import time
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()

# --- 1. CONFIGURATION & CONTEXT ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8000")

# Injecting spatial-temporal awareness into the base prompt drastically reduces hallucinations
CURRENT_CONTEXT = "Current Location: Santa Anita, Jalisco, Mexico. Date: March 2, 2026."

# --- 2. SHARED MEMORY (DOCKER REDIS) ---
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# --- 3. AUTOMATION & AUTHORIZATION TOOLS ---
@tool("write_to_shared_memory")
def write_to_shared_memory(note: str) -> str:
    """Leave a note for other agents about Jalisco 2026 budget findings."""
    try:
        r.lpush("neocloud:shared_state", note)
        # Prevent memory leaks by capping the list to the 50 most recent notes
        r.ltrim("neocloud:shared_state", 0, 49) 
        return "SUCCESS: Finding saved to memory."
    except Exception as e:
        return f"REDIS ERROR: {str(e)}"

@tool("read_shared_memory")
def read_shared_memory(query: str = "") -> str:
    """Read what other agents discovered about the project."""
    try:
        notes = r.lrange("neocloud:shared_state", 0, -1)
        return "\n---\n".join(notes) if notes else "No notes found in memory."
    except Exception as e:
        return f"REDIS ERROR: {str(e)}"

@tool("send_proposal_to_dashboard")
def send_proposal_to_dashboard(plan_markdown: str) -> str:
    """Transmits the final plan to the review screen. REQUIRED before authorization."""
    try:
        response = requests.post(f"{DASHBOARD_URL}/show-proposal", json={"plan": plan_markdown}, timeout=10)
        response.raise_for_status()
        return "SUCCESS: Proposal transmitted to dashboard review screen."
    except requests.exceptions.RequestException as e:
        return f"ERROR: Dashboard bridge communication failed: {str(e)}"

@tool("wait_for_senior_engineer_approval")
def wait_for_senior_engineer_approval(query: str = "") -> str:
    """Pauses execution and polls the dashboard for the Authorize click. Do not skip."""
    print("\n[WAITING] Awaiting Senior Engineer authorization via Dashboard...")
    max_retries = 150 # 5 minutes max wait time (150 attempts * 2 sec)
    attempts = 0
    
    while attempts < max_retries:
        try:
            response = requests.get(f"{DASHBOARD_URL}/check-approval-status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                if data.get("approved"):
                    feedback = data.get("feedback", "Authorized without comments")
                    print(f"[RECEIVED] Authorization confirmed: {feedback}")
                    return f"Mission Authorized. feedback: {feedback}"
                
                # Handled rejection logic in case the Senior Engineer kicks it back
                elif data.get("rejected"):
                    feedback = data.get("feedback", "Rejected without comments")
                    print(f"[REJECTED] Proposal rejected: {feedback}")
                    return f"Mission Rejected. feedback: {feedback}. Revise the plan."
                    
        except requests.exceptions.RequestException:
            pass # Suppress temporary connection drops during polling
        
        time.sleep(2)
        attempts += 1
        
    return "TIMEOUT ERROR: Did not receive authorization from Senior Engineer within 5 minutes. Abort current operation."

# --- 4. LOCAL GLM-4.6V BRAIN (STABILIZED) ---
local_llm = LLM(
    model="openai/zai-org/glm-4.6v-flash",
    base_url=os.getenv("LLM_BASE_URL", "http://192.168.1.90:1234/v1"),
    api_key=os.getenv("LLM_API_KEY", "lm-studio"),
    temperature=0.1, # Lowered for strict financial/analytical determinism
    max_tokens=4096, # Increased to accommodate full markdown reports
    stop=["Observation:", "\nObservation:"],
    timeout=120 # Failsafe if LM Studio hangs
)

# --- 5. FORMATTING INSTRUCTION ---
local_prompt_fix = (
    f"\n\nSYSTEM CONTEXT: {CURRENT_CONTEXT}\n"
    "CRITICAL: Do not use <think> tags. "
    "Respond ONLY with this exact structure:\n"
    "Thought: [your internal reasoning]\n"
    "Action: [exact tool_name]\n"
    "Action Input: {\"arg\": \"value\"}\n"
)

# --- 6. AGENTS ---
auditor = Agent(
    role='Senior Financial Auditor',
    goal='Identify and quantify 2026 FASAR risks in Project 48 for Jalisco public works.',
    backstory='You are an elite Mexican Labor Law expert specializing in NOM-030 and Art. 123 compliance. '
              'You provide highly analytical, data-driven insights.' + local_prompt_fix,
    llm=local_llm,
    tools=[write_to_shared_memory, read_shared_memory],
    verbose=True,
    allow_delegation=False,
    max_iter=10, # Prevents infinite tool-usage loops
    max_execution_time=300 # 5 minutes max lifecycle
)

optimizer = Agent(
    role='Lead Procurement Strategist',
    goal='Optimize construction prices, draft the final strategy, and manage the dashboard authorization loop.',
    backstory='You are a master supply chain specialist. Your sole objective is translating audit risks into a '
              'cost-effective proposal. You MUST push drafts via the dashboard and WAIT for the UI signal.' + local_prompt_fix,
    llm=local_llm,
    tools=[write_to_shared_memory, read_shared_memory, send_proposal_to_dashboard, wait_for_senior_engineer_approval],
    verbose=True,
    allow_delegation=False,
    max_iter=15, 
    max_execution_time=600 # 10 minutes max lifecycle to account for human wait time
)

# --- 7. AUTOMATED TASKS ---
audit_task = Task(
    description='Analyze Project 48 for 2026 labor compliance. Focus strictly on NOM-030 and Art.123 impacts on FASAR. '
                'Document all risks and strictly write them to shared memory.',
    expected_output='A structured Markdown report outlining key 2026 FASAR risks and compliance gaps.',
    agent=auditor
)

review_task = Task(
    description="""
    1. Read shared memory to digest the auditor's findings.
    2. Create a 2026 price optimization plan mitigating the identified FASAR risks.
    3. MANDATORY: Execute 'send_proposal_to_dashboard' to display your plan to the user.
    4. MANDATORY: Immediately execute 'wait_for_senior_engineer_approval' after sending.
    5. If authorized, finalize the report. If rejected, revise the plan based on feedback and repeat steps 3-4.
    """,
    expected_output='The final, dashboard-authorized price optimization plan in Markdown.',
    agent=optimizer,
    context=[audit_task] # Explicitly chains execution logic
)

# --- 8. CREW EXECUTION ---
neocloud_crew = Crew(
    agents=[auditor, optimizer],
    tasks=[audit_task, review_task],
    process=Process.sequential,
    verbose=True,
    memory=False # Disabled CrewAI's default memory since you are manually routing state via Redis
)

if __name__ == "__main__":
    print("\n[SYSTEM] Initiating Mission (7800X3D Dashboard Bridge Active)...")
    neocloud_crew.kickoff()