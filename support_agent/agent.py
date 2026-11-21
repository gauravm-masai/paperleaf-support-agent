"""
The support agent.

This is the starter version: a friendly assistant with no business and no rules yet.
In Session 1 you give it a job.
"""

import os

from dotenv import load_dotenv
from google.adk.agents import Agent

# Read the settings in the .env file (your Gemini key and the model name).
# The key is never written in code.
load_dotenv()

# The model name is set in ONE place: GEMINI_MODEL in the .env file.
MODEL = os.environ["GEMINI_MODEL"]

# The instruction is the agent's job description. It tells the model how to behave.
INSTRUCTION = """
You are a friendly assistant.
Keep your replies short and polite.
"""

# root_agent is the agent that ADK runs.
root_agent = Agent(
    name="support_agent",
    model=MODEL,
    description="A friendly assistant.",
    instruction=INSTRUCTION,
)
