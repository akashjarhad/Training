"""
app/agent_loop.py
Hand-written ReAct agent that can call RAG search and RTS due date tools.

This is a simple agent loop that:
1. Takes a user query
2. Decides which tool(s) to call based on the query
3. Executes tools
4. Formats a final answer

No LLM is used for tool selection - the agent uses pattern matching to decide
which tool to call. This keeps it deterministic and fast for demonstration.

Usage:
    from app.agent_loop import run_agent
    
    result = run_agent("When is my caste certificate due if I applied on 2026-11-01?")
    print(result["answer"])
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.tools import rag_search, rts_due_date, get_tool_function


def run_agent(
    query: str,
    max_steps: int = 5,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run the hand-written agent on a user query.
    
    Args:
        query: User's question or request
        max_steps: Maximum tool calls allowed (prevents infinite loops)
        verbose: If True, print reasoning steps
    
    Returns:
        {
            "query": str,
            "answer": str,
            "steps": list[dict],  # Tool calls and results
            "final_answer": str,
            "error": str | None
        }
    """
    steps = []
    
    try:
        # Step 1: Analyze query and decide which tool(s) to call
        tool_plan = _plan_tools(query)
        
        if verbose:
            print(f"Query: {query}")
            print(f"Plan: {tool_plan}")
        
        # Step 2: Execute tools
        tool_results = []
        for tool_call in tool_plan["calls"]:
            tool_name = tool_call["tool"]
            tool_args = tool_call["args"]
            
            if verbose:
                print(f"\nCalling {tool_name} with {tool_args}")
            
            tool_fn = get_tool_function(tool_name)
            if not tool_fn:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            result = tool_fn(**tool_args)
            tool_results.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result,
            })
            
            if verbose:
                print(f"Result: {result}")
            
            steps.append({
                "step": len(steps) + 1,
                "action": "tool_call",
                "tool": tool_name,
                "args": tool_args,
                "result": result,
            })
            
            if len(steps) >= max_steps:
                break
        
        # Step 3: Synthesize final answer
        final_answer = _synthesize_answer(query, tool_results)
        
        if verbose:
            print(f"\nFinal answer: {final_answer}")
        
        return {
            "query": query,
            "answer": final_answer,
            "steps": steps,
            "final_answer": final_answer,
            "error": None,
        }
    
    except Exception as exc:
        return {
            "query": query,
            "answer": f"Agent error: {exc}",
            "steps": steps,
            "final_answer": None,
            "error": str(exc),
        }


def _plan_tools(query: str) -> dict[str, Any]:
    """
    Analyze query and decide which tools to call.
    
    Uses pattern matching to detect:
    - Due date queries: "when is X due", "is my X late", "applied on DATE"
    - RAG queries: policy questions, "what is", "how do I"
    
    Returns a plan with tool calls and their arguments.
    """
    query_lower = query.lower()
    calls = []
    
    # Pattern 1: Due date calculation
    # Look for: "due", "late", "overdue", "applied on", date patterns
    has_due_keywords = any(kw in query_lower for kw in [
        "due", "late", "overdue", "deadline", "applied on", "submitted on"
    ])
    
    # Extract date if present (YYYY-MM-DD format)
    date_match = re.search(r'\b(20\d{2}-\d{2}-\d{2})\b', query)
    
    # Extract service name (crude heuristic: look for common service keywords)
    service_keywords = [
        "caste", "income", "domicile", "ration", "water",
        "certificate", "connection", "card", "permit", "license"
    ]
    service_name = None
    for keyword in service_keywords:
        if keyword in query_lower:
            # Extract a few words around the keyword
            words = query_lower.split()
            try:
                idx = words.index(keyword)
                # Take 2 words before and 2 after
                start = max(0, idx - 2)
                end = min(len(words), idx + 3)
                service_name = " ".join(words[start:end])
                break
            except ValueError:
                continue
    
    if has_due_keywords and date_match and service_name:
        # This is a due date query
        calls.append({
            "tool": "rts_due_date",
            "args": {
                "service_name": service_name,
                "application_date": date_match.group(1),
                "count_working_days": False,  # Default to calendar days
            }
        })
    elif has_due_keywords and service_name:
        # Due date query but no date - need to ask user or use RAG
        calls.append({
            "tool": "rag_search",
            "args": {
                "question": query,
                "top_k": 5,
            }
        })
    else:
        # Pattern 2: General RAG query
        # Default to RAG for policy/information questions
        calls.append({
            "tool": "rag_search",
            "args": {
                "question": query,
                "top_k": 5,
            }
        })
    
    return {
        "strategy": "pattern_match",
        "calls": calls,
    }


def _synthesize_answer(query: str, tool_results: list[dict]) -> str:
    """
    Synthesize a final answer from tool results.
    
    Formats the tool outputs into a human-readable response.
    """
    if not tool_results:
        return "I couldn't process your query. Please try rephrasing."
    
    # Get the primary result (first tool call)
    primary = tool_results[0]
    tool_name = primary["tool"]
    result = primary["result"]
    
    if tool_name == "rag_search":
        # Format RAG answer
        answer = result.get("answer", "No answer found.")
        sources = result.get("sources", [])
        
        response = answer
        
        if sources and "I don't know" not in answer:
            response += "\n\n**Sources:**"
            for src in sources[:3]:  # Show top 3 sources
                title = src.get("title", "Unknown")
                page = src.get("page")
                page_str = f", page {page}" if page else ""
                response += f"\n- {title}{page_str}"
        
        return response
    
    elif tool_name == "rts_due_date":
        # Format due date result
        if result.get("error"):
            return f"Error: {result['error']}"
        
        service = result.get("service_name", "Service")
        due_date = result.get("due_date", "unknown")
        is_late = result.get("is_late", False)
        days_until = result.get("days_until_due", 0)
        time_limit = result.get("time_limit_days", "unknown")
        
        response = f"**{service}**\n\n"
        response += f"Statutory time limit: {time_limit} days\n"
        response += f"Application date: {result.get('application_date')}\n"
        response += f"Due date: {due_date}\n\n"
        
        if is_late:
            response += f"⚠️ **OVERDUE** by {abs(days_until)} days\n\n"
            response += "You can file an appeal to the First Appellate Authority within 30 days."
        elif days_until == 0:
            response += "⏰ **Due today**"
        elif days_until > 0:
            response += f"✓ Still on time ({days_until} days remaining)"
        else:
            response += f"⚠️ Overdue by {abs(days_until)} days"
        
        return response
    
    return "Tool result received but couldn't format answer."


def main():
    """CLI demo for the agent."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.agent_loop 'Your query here'")
        print("\nExamples:")
        print('  python -m app.agent_loop "What is the time limit for caste certificate?"')
        print('  python -m app.agent_loop "Is my water connection due if I applied on 2026-11-01?"')
        return 1
    
    query = " ".join(sys.argv[1:])
    result = run_agent(query, verbose=True)
    
    print("\n" + "="*60)
    print("FINAL ANSWER:")
    print("="*60)
    print(result["answer"])
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
