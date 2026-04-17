import warnings
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality.*")

import datetime
import os
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.tools import search_flights, search_hotels, calculate_budget

# Read system prompt once at import (just file I/O, safe)
_prompt_path = os.path.join(os.path.dirname(__file__), "..", "system_prompt.txt")
with open(_prompt_path, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = "".join(l for l in f if not l.strip().startswith("#"))

tools_list = [search_flights, search_hotels, calculate_budget]

# Lazy-initialized graph — created on first request, not at import time
# This ensures /health responds even before OPENAI_API_KEY is validated
_graph = None

def _build_graph():
    llm = ChatOpenAI(model="gpt-4o-mini")
    llm_with_tools = llm.bind_tools(tools_list)

    class AgentState(TypedDict):
        messages: Annotated[list, add_messages]

    def agent_node(state: AgentState):
        now = datetime.datetime.now()
        vn_days = {0: "Thứ Hai", 1: "Thứ Ba", 2: "Thứ Tư",
                   3: "Thứ Năm", 4: "Thứ Sáu", 5: "Thứ Bảy", 6: "Chủ Nhật"}
        current_date = f"{vn_days[now.weekday()]}, ngày {now.strftime('%d/%m/%Y')}"
        sys_msg = SystemMessage(content=SYSTEM_PROMPT + f"\n\n[THÔNG TIN HỆ THỐNG]\nHôm nay là: {current_date}.")

        raw_msgs = state["messages"]
        trimmed = raw_msgs[-10:] if len(raw_msgs) > 10 else raw_msgs
        while trimmed and trimmed[0].type == "tool":
            trimmed = trimmed[1:]

        return {"messages": [llm_with_tools.invoke([sys_msg] + trimmed)]}

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools_list))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")

    return builder.compile(checkpointer=MemorySaver())


def run_agent(question: str, thread_id: str) -> str:
    global _graph
    if _graph is None:
        _graph = _build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = _graph.invoke({"messages": [HumanMessage(content=question)]}, config)
    return result["messages"][-1].content
