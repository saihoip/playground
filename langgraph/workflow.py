import os
from typing import Annotated, List, Optional, TypedDict, Literal

from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from langchain_deepseek import ChatDeepSeek

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from tavily import TavilyClient

load_dotenv()
llm = ChatDeepSeek(model="deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"))
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


class AgentState(TypedDict):
    task: Optional[str]
    plan: Optional[str]
    web_content: Optional[str]
    code: Optional[str]
    report: Optional[str]
    workflow_needed: bool
    general_answer: Optional[str]
    messages: Annotated[List[BaseMessage], add_messages]


def decide_initial_path(
    state: AgentState,
) -> Literal["general_question_handler", "planner"]:
    """Determines if the initial query needs general handling or a full workflow."""
    if state["workflow_needed"] is None:  # Initial check
        return "general_question_handler"
    elif state["workflow_needed"] == True:
        return "planner"
    else:  # If workflow_needed is False, it means general_question_handler already handled it
        return END


def general_question_handler(state: AgentState) -> AgentState:
    print("---GENERAL QUESTION HANDLER---")
    task = state["task"]

    # Prompt to determine if a full workflow is needed
    workflow_check_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Analyze the following user query. If it can be answered directly and concisely without needing a multi-step workflow (planning, web scraping, coding, reporting), provide that direct answer. Otherwise, respond with 'WORKFLOW_NEEDED' indicating a full workflow is required.",
            ),
            ("user", "{query}"),
        ]
    )
    workflow_check_chain = workflow_check_prompt | llm
    workflow_check_response_content = workflow_check_chain.invoke(
        {"query": task}
    ).content

    if "WORKFLOW_NEEDED" in workflow_check_response_content:
        print("Workflow needed.")
        return {"workflow_needed": True, task: task}
    else:
        general_answer = workflow_check_response_content.strip()
        print(f"General question detected. Answer: {general_answer}")
        return {"workflow_needed": False, "general_answer": general_answer}


def planner(state: AgentState) -> AgentState:
    print("---PLANNER AGENT---")
    task = state["task"]
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are a Planner Agent. Your job is to break down the user's request into a clear and actionable plan using a markdown TODO list.

Only the following agents can be used to perform the tasks:
web_scraper_agent: gather relevant information from the internet
reporter-agent: summarize the gathered relevant information

Instructions:
- Use general language to describe tasks. Do not mention specific tools or agents.
- Decompose the request into logical, sequential steps.
- Each step must be something the listed agents can do.
- Format your response strictly as a markdown TODO list.
- Do not include any explanations, reasoning, or extra text.
- Do not write anything to the markdown TODO list.

Example Output:
Title: <Concise title of the plan>
- [ ] <Step 1>
- [ ] <Step 2>
- [ ] ...
""",
            ),
            ("user", "{task}"),
        ]
    )
    chain = prompt | llm
    response = chain.invoke({"task": task})
    print(f"--- Planner Output ---")
    print(f"Task: {response.content}")
    return {"plan": response.content}


def route_next_step(
    state: AgentState,
) -> Literal["web_scraper", "coder", "reporter", "planner", "end"]:
    print("---ROUTER (LLM Classifier)---")
    if not state["workflow_needed"]:
        return "end"

    todo_lines = state["plan"].strip().splitlines()
    for step in todo_lines:
        if "- [ ]" in step:
            current_task_description = step.replace("- [ ] ", "").strip()

            # LLM call to classify the task
            classification_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """
You are a task classifier. Your job is to assign a single category to each task description based on its primary intent. The available categories are:

- web_scraping – For tasks that involve gathering or researching information from online sources.
- coding – For tasks that involve writing, modifying, or executing code.
- reporting – For tasks that involve summarizing findings, generating reports, or explaining results.

Instructions:

Given a task description, respond with only the most appropriate category name from the list above.

Examples:

- [ ] Gather information about the origins and initial development of Node.js
web_scraping

- [ ] Collect details about key milestones and version releases of Node.js
web_scraping

- [ ] Find information about the creators and major contributors to Node.js
web_scraping

- [ ] Research the impact and adoption trends of Node.js over time
web_scraping

- [ ] Summarize the gathered information into a coherent historical overview
reporting
""",
                    ),
                    ("user", "{task_description}"),
                ]
            )
            classifier_chain = classification_prompt | llm
            category = (
                classifier_chain.invoke({"task_description": current_task_description})
                .content.strip()
                .lower()
            )

            print(f"Task '{current_task_description}' classified as: {category}")

            if "web_scraping" in category:
                return "web_scraper"
            elif "coding" in category:
                return "coder"
            elif "reporting" in category:
                return "reporter"
            elif (
                "planning_refinement" in category
            ):  # For tasks not directly actionable by agents
                return "planner"
            else:
                print(
                    f"Warning: Unknown category '{category}'. Routing to planner for refinement."
                )
                return "planner"  # Fallback to planner if classification is unclear

    return "end"


def web_scraper(state: AgentState) -> AgentState:
    print("---WEB_SCRAPER---")
    plan = state["plan"]
    content = state["web_content"] if "web_content" in state else ""

    todo_lines = state["plan"].strip().splitlines()

    # Find the first unchecked item in the todo list
    for step in todo_lines:
        if "- [ ]" in step:
            # Perform web scraping based on the step
            search_query = step.replace("- [ ]", "").strip()
            content = content + f"Performing web search for: {search_query}\n"
            print(f"Performing web search for: {search_query}")
            response = tavily_client.search(search_query, max_results=1)
            print(f"Search results: {response['results']}\n")
            content = content + f"Search results: {response['results'][0]['content']}\n"
            print(f"connt: {content}")

            # Update the state with the gathered content
            updated_plan = plan.replace("- [ ]", "- [x]", 1)
            print(f"Update plan: {updated_plan}")
            return {"plan": updated_plan, "web_content": content}

    return END


def coder(state: AgentState) -> AgentState:
    print("---CODER---")
    plan = state["plan"]

    updated_plan = plan.replace("- [ ]", "- [x]", 1)
    print(f"Update plan: {updated_plan}")

    return {"plan": updated_plan}


def reporter(state: AgentState) -> AgentState:
    print("---REPORTER---")
    web_content = state["web_content"]

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are a professional reporter. Compile all the provided information into a clear, polished, and concise report. 
""",
            ),
            ("user", "{content}"),
        ]
    )
    chain = prompt | llm
    response = chain.invoke({"content": web_content})
    print(f"--- Reporter Output ---")
    print(f"Report: {response.content}")
    return {"report": response.content}


workflow = StateGraph(AgentState)

# Add nodes for each agent and the general question handler
workflow.add_node("general_question_handler", general_question_handler)
workflow.add_node("planner", planner)
workflow.add_node("web_scraper", web_scraper)
workflow.add_node("coder", coder)
workflow.add_node("reporter", reporter)

# Set the entry point
workflow.set_entry_point("general_question_handler")

# Conditional edge from general_question_handler
workflow.add_conditional_edges(
    "general_question_handler", decide_initial_path, {"planner": "planner", END: END}
)

# Planner always goes to the router node to decide the next step
workflow.add_conditional_edges(
    "planner",  # Source node: After 'planner' completes its state update
    route_next_step,  # Conditional function that decides the next step (e.g., "web_scraper", "coder")
    {
        "web_scraper": "web_scraper",  # Map string output from route_next_step to node names
        "coder": "coder",
        "reporter": "reporter",
        "end": END,  # If route_next_step returns "end"
    },
)


# After 'web_scraper' completes, use 'route_next_step' to determine the next agent.
workflow.add_conditional_edges(
    "web_scraper",  # Source node: After 'web_scraper' completes its state update
    route_next_step,  # Conditional function
    {
        "web_scraper": "web_scraper",  # Allow returning to web_scraper for sequential searches
        "coder": "coder",
        "reporter": "reporter",
        "end": END,
    },
)

# After 'coder' completes, use 'route_next_step' to determine the next agent.
workflow.add_conditional_edges(
    "coder",  # Source node: After 'coder' completes its state update
    route_next_step,  # Conditional function
    {
        "web_scraper": "web_scraper",
        "reporter": "reporter",
        "end": END,
    },
)


# Reporter is the final step for a full workflow
workflow.add_edge("reporter", END)

# Compile the graph
app = workflow.compile()

import time  # for Unix timestamp
from datetime import datetime

from IPython.display import Image, display

try:
    img_bytes = app.get_graph().draw_mermaid_png()
    timestamp = int(time.time())
    filename = f"images/graph_{timestamp}.png"
    with open(filename, "wb") as f:
        f.write(img_bytes)
except Exception:
    # This requires some extra dependencies and is optional
    pass


__all__ = ["app"]
