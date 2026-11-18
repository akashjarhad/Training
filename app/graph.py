"""
app/graph.py
LangGraph-based agent with memory and approval step for AapleSeva.

This agent uses LangGraph to orchestrate tool calls with:
- Conversational memory (tracks context across multiple turns)
- Human-in-the-loop approval before executing sensitive tools
- Structured state management
- Graph-based execution flow

The graph has these nodes:
    1. agent: LLM decides which tool to call (or finishes)
    2. approval: Human approves or rejects tool calls
    3. tools: Execute approved tool calls
    4. END: Terminal state

Usage:
    from app.graph import create_agent_graph, run_agent_graph
    
    graph = create_agent_graph()
    result = run_agent_graph(graph, "What is the time limit for caste certificate?")
    print(result["messages"][-1]["content"])
"""

from __future__ import annotations

import json
from typing import Any, Literal

from app.llm import get_provider
from app.tools import rag_search, rts_due_date, TOOL_DEFINITIONS


# State schema for the agent graph
class AgentState(dict):
    """
    State passed between graph nodes.
    
    Fields:
        messages: Conversation history (list of dicts with role/content)
        pending_tool_calls: Tool calls waiting for approval
        tool_results: Results from executed tools
        approval_status: "pending", "approved", "rejected", or None
        loop_count: Number of agent iterations
    """
    pass


def create_agent_graph():
    """
    Create the LangGraph agent with approval workflow.
    
    Returns a compiled graph ready for execution.
    
    Note: This is a simplified implementation that doesn't require LangGraph
    as a dependency. In production, you would use:
        from langgraph.graph import StateGraph, END
        
    For now, we simulate the graph structure with a dict-based approach.
    """
    # We'll return a graph config that can be executed by run_agent_graph
    return {
        "nodes": {
            "agent": agent_node,
            "approval": approval_node,
            "tools": tools_node,
        },
        "edges": {
            "agent": route_after_agent,
            "approval": route_after_approval,
            "tools": lambda state: "agent",  # Loop back to agent
        },
        "entry_point": "agent",
    }


def agent_node(state: AgentState) -> AgentState:
    """
    Agent decision node: LLM decides next action.
    
    The LLM can either:
    - Call a tool (returns tool call JSON)
    - Provide final answer (returns text response)
    """
    messages = state.get("messages", [])
    
    # Build prompt with tool definitions
    system_prompt = _build_system_prompt()
    
    # Add tool definitions to context
    tool_context = "\n\n**Available Tools:**\n"
    for tool_def in TOOL_DEFINITIONS:
        tool_context += f"\n- **{tool_def['name']}**: {tool_def['description']}"
    
    # Create messages for LLM
    llm_messages = [
        {"role": "system", "content": system_prompt + tool_context}
    ] + messages
    
    # Call LLM
    try:
        provider = get_provider()
        response = provider.chat(llm_messages, temperature=0.2, max_tokens=800)
        response_text = response.text
    except Exception as exc:
        response_text = f"Error calling LLM: {exc}"
    
    # Parse response - check if it's a tool call or final answer
    tool_calls = _extract_tool_calls(response_text)
    
    if tool_calls:
        # LLM wants to call tools - add to state for approval
        state["pending_tool_calls"] = tool_calls
        state["approval_status"] = "pending"
        messages.append({
            "role": "assistant",
            "content": f"I need to call these tools: {json.dumps(tool_calls, indent=2)}"
        })
    else:
        # LLM provided final answer
        messages.append({
            "role": "assistant",
            "content": response_text
        })
        state["pending_tool_calls"] = None
        state["approval_status"] = None
    
    state["messages"] = messages
    state["loop_count"] = state.get("loop_count", 0) + 1
    
    return state


def approval_node(state: AgentState) -> AgentState:
    """
    Human approval node: ask user to approve tool calls.
    
    In a real implementation, this would pause execution and wait for
    user input via a UI. For this demo, we auto-approve.
    """
    pending = state.get("pending_tool_calls", [])
    
    if not pending:
        state["approval_status"] = "approved"
        return state
    
    # Auto-approve for demo (in production, this would be interactive)
    print("\n⚠️ APPROVAL REQUIRED:")
    print("The agent wants to call these tools:")
    for call in pending:
        print(f"  - {call['tool']}: {call['args']}")
    print("Auto-approving for demo...")
    
    state["approval_status"] = "approved"
    
    return state


def tools_node(state: AgentState) -> AgentState:
    """
    Tool execution node: run approved tool calls.
    """
    tool_calls = state.get("pending_tool_calls", [])
    
    if not tool_calls:
        return state
    
    tool_results = []
    for call in tool_calls:
        tool_name = call["tool"]
        tool_args = call["args"]
        
        # Execute tool
        if tool_name == "rag_search":
            result = rag_search(**tool_args)
        elif tool_name == "rts_due_date":
            result = rts_due_date(**tool_args)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
        
        tool_results.append({
            "tool": tool_name,
            "args": tool_args,
            "result": result,
        })
    
    # Add tool results to messages
    messages = state.get("messages", [])
    for tr in tool_results:
        messages.append({
            "role": "tool",
            "tool": tr["tool"],
            "content": json.dumps(tr["result"], ensure_ascii=False)
        })
    
    state["messages"] = messages
    state["tool_results"] = tool_results
    state["pending_tool_calls"] = None
    state["approval_status"] = None
    
    return state


def route_after_agent(state: AgentState) -> Literal["approval", "END"]:
    """
    Routing function: decide next node after agent.
    
    If agent wants to call tools -> approval
    If agent provided final answer -> END
    """
    pending = state.get("pending_tool_calls")
    loop_count = state.get("loop_count", 0)
    
    # Safety: max 5 iterations
    if loop_count >= 5:
        return "END"
    
    if pending:
        return "approval"
    else:
        return "END"


def route_after_approval(state: AgentState) -> Literal["tools", "END"]:
    """
    Routing function: decide next node after approval.
    
    If approved -> tools
    If rejected -> END
    """
    status = state.get("approval_status")
    
    if status == "approved":
        return "tools"
    else:
        return "END"


def run_agent_graph(
    graph: dict,
    query: str,
    conversation_history: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Execute the agent graph on a query.
    
    Args:
        graph: Graph created by create_agent_graph()
        query: User's question
        conversation_history: Previous messages for memory (optional)
    
    Returns:
        {
            "messages": list[dict],     # Full conversation
            "final_answer": str,       # Last assistant message
            "tool_calls": list[dict],  # Tools that were called
            "state": dict,            # Final state
        }
    """
    # Initialize state
    state: AgentState = {
        "messages": conversation_history or [],
        "pending_tool_calls": None,
        "tool_results": [],
        "approval_status": None,
        "loop_count": 0,
    }
    
    # Add user query
    state["messages"].append({
        "role": "user",
        "content": query
    })
    
    # Execute graph
    current_node = graph["entry_point"]
    
    while current_node != "END":
        # Execute current node
        node_fn = graph["nodes"][current_node]
        state = node_fn(state)
        
        # Determine next node
        edge_fn = graph["edges"][current_node]
        current_node = edge_fn(state)
    
    # Extract final answer
    messages = state["messages"]
    final_answer = ""
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and "content" in msg:
            final_answer = msg["content"]
            break
    
    return {
        "messages": messages,
        "final_answer": final_answer,
        "tool_calls": [
            tr for tr in state.get("tool_results", [])
        ],
        "state": state,
    }


def _build_system_prompt() -> str:
    """Build the system prompt for the agent LLM."""
    return """You are an AapleSeva assistant helping citizens with Maharashtra's Right to Service Act.

You have access to two tools:
1. rag_search: Search documents and answer policy questions
2. rts_due_date: Calculate service delivery due dates

When the user asks a question:
- If they want policy information or general questions → use rag_search
- If they want to calculate a due date → use rts_due_date
- If the question is already answered, provide a direct response

To call a tool, respond with JSON in this format:
{
  "tool_call": {
    "tool": "tool_name",
    "args": {
      "param1": "value1",
      "param2": "value2"
    }
  }
}

If you have enough information to answer directly, just provide the answer as plain text.

Be concise, accurate, and cite sources when using rag_search results."""


def _extract_tool_calls(text: str) -> list[dict] | None:
    """
    Extract tool calls from LLM response.
    
    Looks for JSON with "tool_call" key or direct tool references.
    Returns None if no tool calls found.
    """
    # Try to parse as JSON
    try:
        data = json.loads(text)
        if "tool_call" in data:
            return [data["tool_call"]]
        return None
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from text
    import re
    json_match = re.search(r'\{[^}]*"tool_call"[^}]*\}', text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            if "tool_call" in data:
                return [data["tool_call"]]
        except json.JSONDecodeError:
            pass
    
    return None


def main():
    """CLI demo for LangGraph agent."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.graph 'Your query here'")
        print("\nExamples:")
        print('  python -m app.graph "What is the time limit for caste certificate?"')
        print('  python -m app.graph "Is my water connection due if I applied on 2026-11-01?"')
        return 1
    
    query = " ".join(sys.argv[1:])
    
    print(f"Query: {query}\n")
    print("Creating agent graph...")
    graph = create_agent_graph()
    
    print("Running agent...\n")
    result = run_agent_graph(graph, query)
    
    print("\n" + "="*60)
    print("FINAL ANSWER:")
    print("="*60)
    print(result["final_answer"])
    
    if result["tool_calls"]:
        print("\n" + "="*60)
        print("TOOLS USED:")
        print("="*60)
        for call in result["tool_calls"]:
            print(f"- {call['tool']}: {call['args']}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
