import warnings
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality.*")

import datetime
import os
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.tools import search_flights, search_hotels, calculate_budget

# Read system prompt, strip developer comment lines
_prompt_path = os.path.join(os.path.dirname(__file__), "..", "system_prompt.txt")
with open(_prompt_path, "r", encoding="utf-8") as f:
    raw_lines = f.readlines()
    SYSTEM_PROMPT = "".join(l for l in raw_lines if not l.strip().startswith("#"))

# State
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# LLM + tools
tools_list = [search_flights, search_hotels, calculate_budget]
llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = llm.bind_tools(tools_list)

# Agent node
def agent_node(state: AgentState):
    now = datetime.datetime.now()
    vn_days = {0: "Thứ Hai", 1: "Thứ Ba", 2: "Thứ Tư", 3: "Thứ Năm", 4: "Thứ Sáu", 5: "Thứ Bảy", 6: "Chủ Nhật"}
    current_date = f"{vn_days[now.weekday()]}, ngày {now.strftime('%d/%m/%Y')}"
    system_instruction = SYSTEM_PROMPT + f"\n\n[QUAN TRỌNG - THÔNG TIN HỆ THỐNG]\nHôm nay là: {current_date}."
    sys_msg = SystemMessage(content=system_instruction)

    raw_msgs = state["messages"]
    if len(raw_msgs) > 10:
        trimmed_msgs = raw_msgs[-10:]
        while trimmed_msgs and trimmed_msgs[0].type == "tool":
            trimmed_msgs = trimmed_msgs[1:]
    else:
        trimmed_msgs = raw_msgs

    response = llm_with_tools.invoke([sys_msg] + trimmed_msgs)
    return {"messages": [response]}

# Build graph
builder = StateGraph(AgentState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools_list))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

def run_agent(question: str, thread_id: str) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"messages": [HumanMessage(content=question)]}, config)
    return result["messages"][-1].content
