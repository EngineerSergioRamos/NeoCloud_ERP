import os
from crewai import Agent, Task, Crew

# Local LM Studio Config
os.environ["OPENAI_API_BASE"] = "http://localhost:1234/v1"
os.environ["OPENAI_API_KEY"] = "lm-studio"

# 1. THE LABOR SPECIALIST (LFT/LSS 2026)
labor_expert = Agent(
    role='Mexican Labor Law Consultant',
    goal='Determine the exact FASAR 2026 formula for construction workers in Jalisco.',
    backstory='''Expert in the 2026 UMA values and the newest reformations to the 
    Ley Federal del Trabajo regarding vacation days and IMSS quotas.''',
    verbose=True
)

# TASK: DEFINE THE ENGINE
task_logic = Task(
    description='''Write a Python class 'FasarEngine' that calculates the 
    Factor de Salario Real. It must include the 2026 UMA and risk premiums.''',
    expected_output='A Python class with a .calculate(base_salary) method.',
    agent=labor_expert
)

crew = Crew(agents=[labor_expert], tasks=[task_logic])
print(crew.kickoff())