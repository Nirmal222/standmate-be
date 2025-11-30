import asyncio
import json
import uuid
import time
import os
from typing import List, TypedDict, Generator, Dict, Any, Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- 1. Pydantic Models for Data and API ---
from pydantic import BaseModel, Field

class Task(BaseModel):
    """The strict structure for a single task card streamed to the frontend."""
    id: str = Field(description="A unique UUID for the task.")
    title: str = Field(description="A concise, actionable title for the task.")
    description: str = Field(description="A detailed explanation of the task, its goal, and expected outcomes.")
    tags: List[str] = Field(description="A list of relevant category tags (e.g., 'Backend', 'UI', 'DevOps').")

class ProjectInput(BaseModel):
    """The input structure for the API endpoint."""
    prompt: str = Field(description="The high-level project idea provided by the user.")

class TaskGeneration(BaseModel):
    """Output schema for the LLM to generate the next task or signal completion."""
    task: Optional[Task] = Field(default=None, description="The next task to be added to the plan.")
    is_finished: bool = Field(default=False, description="Set to True if the plan is complete and no more tasks are needed.")


# --- 2. LangGraph Agent Setup ---
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

# Define State
class AgentState(TypedDict):
    """The state passed between nodes in the LangGraph."""
    prompt: str
    tasks: List[Task]
    finished: bool

# Initialize LLM
# Ensure GOOGLE_API_KEY is set in your environment or .env file
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)

# Define the Node
def generate_task_node(state: AgentState) -> Dict[str, Any]:
    """
    Generates the next task in the plan based on the user's prompt and existing tasks.
    """
    prompt = state["prompt"]
    current_tasks = state["tasks"]
    
    # Construct context from existing tasks
    task_history = "\n".join([f"- {t.title}: {t.description}" for t in current_tasks])
    
    system_prompt = """You are an expert project planner and technical architect.
    Your goal is to break down a high-level project idea into a series of actionable, technical tasks.
    
    You must generate tasks ONE BY ONE in a logical implementation order.
    
    For each step:
    1. Review the Project Idea.
    2. Review the Tasks already generated.
    3. Determine the NEXT logical task required.
    4. If the plan is complete and covers all aspects (Backend, Frontend, DevOps, Testing), set 'is_finished' to True.
    
    Be specific, technical, and practical.
    """
    
    user_message = f"""Project Idea: {prompt}

    Already Generated Tasks:
    {task_history if task_history else "No tasks generated yet."}

    Generate the next task or finish the plan.
    """
    
    # Bind the structured output schema
    structured_llm = llm.with_structured_output(TaskGeneration)
    
    # Call LLM
    try:
        result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])
        
        if result.is_finished:
            return {"finished": True}
        
        if result.task:
            # Ensure ID is present
            if not result.task.id:
                result.task.id = str(uuid.uuid4())
            
            return {
                "tasks": current_tasks + [result.task],
                "finished": False
            }
        else:
             return {"finished": True}
             
    except Exception as e:
        print(f"LLM Error: {e}")
        return {"finished": True}


# Define the Graph
workflow = StateGraph(AgentState)

workflow.add_node("planner", generate_task_node)
workflow.set_entry_point("planner")

def should_continue(state: AgentState) -> str:
    if state.get("finished", False):
        return END
    if len(state["tasks"]) >= 10:
        return END
    return "planner"

workflow.add_conditional_edges(
    "planner",
    should_continue,
    {
        "planner": "planner",
        END: END
    }
)

langgraph_app = workflow.compile()


# --- 3. FastAPI Implementation ---

app = FastAPI(title="Streaming Task Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def task_stream_generator(project_prompt: str) -> Generator[bytes, None, None]:
    """
    Asynchronous generator that drives LangGraph execution and yields
    complete, serialized task objects as NDJSON.
    """
    initial_state = AgentState(prompt=project_prompt, tasks=[], finished=False)
    
    print(f"Starting generation for prompt: {project_prompt}")
    
    num_tasks_sent = 0

    try:
        # Stream the graph execution
        async for state_change in langgraph_app.astream(initial_state, stream_mode="values"):
            
            current_tasks = state_change.get('tasks', [])
            
            if len(current_tasks) > num_tasks_sent:
                for i in range(num_tasks_sent, len(current_tasks)):
                    new_task = current_tasks[i]
                    
                    # --- UI SIMULATION START ---
                    # 1. Yield Structure (Empty)
                    initial_task_data = new_task.dict()
                    initial_task_data['description'] = ""
                    yield f"data: {json.dumps(initial_task_data, default=str)}\n\n".encode("utf-8")
                    
                    # 2. Simulate Typing
                    full_description = new_task.description
                    chunk_size = 4
                    for j in range(0, len(full_description), chunk_size):
                        current_desc = full_description[:j+chunk_size]
                        
                        partial_task_data = initial_task_data.copy()
                        partial_task_data['description'] = current_desc
                        yield f"data: {json.dumps(partial_task_data, default=str)}\n\n".encode("utf-8")
                        await asyncio.sleep(0.01)
                    
                    # 3. Yield Final
                    yield f"data: {json.dumps(new_task.dict(), default=str)}\n\n".encode("utf-8")
                    # --- UI SIMULATION END ---
                
                num_tasks_sent = len(current_tasks)
            
            if state_change.get('finished'):
                yield f"data: {json.dumps({'status': 'completed'})}\n\n".encode("utf-8")
                break
            
    except Exception as e:
        print(f"STREAMING ERROR: {e}")
        yield f"data: {json.dumps({'status': 'error', 'detail': str(e)})}\n\n".encode("utf-8")
        

@app.get("/api/stream_tasks")
async def stream_tasks(prompt: str):
    return StreamingResponse(
        task_stream_generator(prompt),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    print("FastAPI server starting on http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
