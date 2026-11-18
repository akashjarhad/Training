# Agent System for AapleSeva

## Overview

The agent system adds autonomous decision-making to AapleSeva, allowing the assistant to intelligently choose and execute tools based on user queries. Two implementations are provided:

1. **Hand-written agent** (`app/agent_loop.py`) - Simple pattern-matching agent
2. **LangGraph agent** (`app/graph.py`) - Sophisticated graph-based agent with memory and approval

## Tools

### 1. `rag_search`
Semantic search over documents with LLM-generated answers.

**Use when:** User asks about RTS Act provisions, service details, policies

**Example:**
```python
from app.tools import rag_search

result = rag_search("What is the time limit for caste certificate?")
print(result["answer"])
# "The time limit is 21 days [RTS Notified Services, page 3]"
```

### 2. `rts_due_date`
Calculate statutory due date from application date.

**Use when:** User wants to know service delivery deadline or check if overdue

**Example:**
```python
from app.tools import rts_due_date

result = rts_due_date(
    service_name="caste certificate",
    application_date="2026-11-01",
    count_working_days=False  # True to exclude weekends/holidays
)

print(f"Due: {result['due_date']}")
print(f"Late: {result['is_late']}")
```

**Working Days Mode:**
- **count_working_days=False** (default): Calendar days (simpler, matches most services)
- **count_working_days=True**: Business days excluding weekends + Maharashtra holidays

**Holiday List:** Includes 2026-2027 Maharashtra public holidays (Republic Day, Holi, Diwali, etc.)

## Hand-Written Agent (app/agent_loop.py)

Simple, deterministic agent using pattern matching to decide which tool to call.

**How it works:**
1. Parse query for keywords ("due", "late", date patterns, service names)
2. If due date query + date + service → call `rts_due_date`
3. Otherwise → call `rag_search`
4. Format result into human-readable answer

**Advantages:**
- No LLM needed for tool selection (fast, deterministic)
- Easy to understand and debug
- No external dependencies

**Limitations:**
- Cannot handle complex multi-step reasoning
- No conversation memory
- Limited to predefined patterns

**Usage:**
```bash
# CLI
python -m app.agent_loop "What is the time limit for caste certificate?"

# Programmatic
from app.agent_loop import run_agent

result = run_agent(
    "Is my water connection due if I applied on 2026-11-01?",
    verbose=True
)
print(result["answer"])
```

## LangGraph Agent (app/graph.py)

Sophisticated agent using graph-based execution flow with LLM decision-making.

**Features:**
- **LLM-based tool selection**: Decides which tool to call based on understanding, not patterns
- **Conversation memory**: Remembers context across multiple turns
- **Human-in-the-loop approval**: Asks permission before executing tools
- **Multi-step reasoning**: Can call multiple tools in sequence

**Graph Structure:**
```
START → agent → approval → tools → agent → ... → END
         ↓                                          ↑
         └──────────────────────────────────────────┘
          (if no tools needed)
```

**Nodes:**
- **agent**: LLM decides next action (call tool or answer directly)
- **approval**: Human approves tool calls (auto-approved in current impl)
- **tools**: Execute approved tools
- **END**: Terminal state

**State Management:**
```python
{
    "messages": [               # Conversation history
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
        {"role": "tool", "tool": "rag_search", "content": "{...}"}
    ],
    "pending_tool_calls": [...],  # Awaiting approval
    "tool_results": [...],        # Completed tools
    "approval_status": "approved",
    "loop_count": 2
}
```

**Usage:**
```bash
# CLI
python -m app.graph "What is the time limit for caste certificate?"

# Programmatic
from app.graph import create_agent_graph, run_agent_graph

graph = create_agent_graph()
result = run_agent_graph(
    graph=graph,
    query="Is my water connection due if I applied on 2026-11-01?",
    conversation_history=[  # Optional: previous conversation
        {"role": "user", "content": "What services does AapleSeva provide?"},
        {"role": "assistant", "content": "..."}
    ]
)

print(result["final_answer"])
print(f"Tools used: {[c['tool'] for c in result['tool_calls']]}")
```

## POST /agent API Endpoint

FastAPI endpoint for the LangGraph agent (added to `app/main.py`).

**Request:**
```json
{
  "query": "Is my caste certificate due if I applied on 2026-11-01?",
  "conversation_history": [
    {"role": "user", "content": "What is the time limit?"},
    {"role": "assistant", "content": "21 days"}
  ]
}
```

**Response:**
```json
{
  "query": "Is my caste certificate due if I applied on 2026-11-01?",
  "answer": "✓ Still on time (20 days remaining)\n\nStatutory time limit: 21 days\nDue date: 2026-11-22",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    {"role": "tool", "tool": "rts_due_date", "content": "{...}"}
  ],
  "tool_calls": [
    {
      "tool": "rts_due_date",
      "args": {
        "service_name": "caste certificate",
        "application_date": "2026-11-01"
      },
      "result": {...}
    }
  ],
  "conversation_id": null
}
```

**Start server:**
```bash
cd Training
python -m uvicorn app.main:app --reload
# Visit http://127.0.0.1:8000/docs for interactive API
```

**Test:**
```bash
curl -X POST http://127.0.0.1:8000/agent \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Is my caste certificate due if I applied on 2026-11-01?"
  }'
```

## Tool Architecture

### Tool Definition Format
Tools are defined in `app/tools.py` with metadata for LangGraph/LangChain:

```python
TOOL_DEFINITIONS = [
    {
        "name": "rag_search",
        "description": "Search documents and answer questions...",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", ...},
                "top_k": {"type": "integer", "default": 5}
            },
            "required": ["question"]
        }
    },
    ...
]
```

### Adding New Tools

1. **Write the function** in `app/tools.py`:
```python
def my_new_tool(param: str) -> dict:
    """Tool description."""
    return {"result": "..."}
```

2. **Add metadata**:
```python
TOOL_DEFINITIONS.append({
    "name": "my_new_tool",
    "description": "When to use this tool...",
    "parameters": {...}
})
```

3. **Register in dispatcher**:
```python
def get_tool_function(name: str):
    tools = {
        "rag_search": rag_search,
        "rts_due_date": rts_due_date,
        "my_new_tool": my_new_tool,  # Add here
    }
    return tools.get(name)
```

4. **Update agent logic** (hand-written agent only; LangGraph agent auto-discovers)

## Comparison: Hand-Written vs LangGraph

| Feature | Hand-Written | LangGraph |
|---------|-------------|-----------|
| **Tool Selection** | Pattern matching | LLM reasoning |
| **Conversation Memory** | ❌ No | ✅ Yes |
| **Multi-step Reasoning** | ❌ Limited | ✅ Yes |
| **Human Approval** | ❌ No | ✅ Yes |
| **Complexity** | Simple (~200 lines) | Moderate (~400 lines) |
| **Dependencies** | None | LLM calls |
| **Speed** | Fast (no LLM) | Slower (LLM overhead) |
| **Use Case** | Demo, simple queries | Production, complex queries |

## Examples

### Example 1: Policy Question (RAG)
```bash
python -m app.agent_loop "What are the three levels of appellate authority?"
```

**Agent reasoning:**
1. No due date keywords → use `rag_search`
2. Call: `rag_search(question="What are the three levels...", top_k=5)`
3. Format answer with sources

**Output:**
```
The three levels are: Designated Officer, First Appellate Authority, 
Second Appellate Authority [RTS Act 2015, page 2]

**Sources:**
- RTS Act 2015, page 2
- RTS Rules Gazette, page 5
```

### Example 2: Due Date Calculation
```bash
python -m app.agent_loop "Is my water connection due if I applied on 2026-11-01?"
```

**Agent reasoning:**
1. Has "due" + date + service → use `rts_due_date`
2. Call: `rts_due_date(service_name="water connection", application_date="2026-11-01")`
3. Format result with status (late/on-time)

**Output:**
```
**New water connection**

Statutory time limit: 15 days
Application date: 2026-11-01
Due date: 2026-11-16

✓ Still on time (14 days remaining)
```

### Example 3: Multi-Turn Conversation (LangGraph only)
```python
from app.graph import create_agent_graph, run_agent_graph

graph = create_agent_graph()

# Turn 1
result1 = run_agent_graph(graph, "What is the time limit for caste certificate?")
# Answer: "21 days [RTS Notified Services, page 3]"

# Turn 2: Remembers context
result2 = run_agent_graph(
    graph,
    "If I applied on 2026-11-01, when is it due?",
    conversation_history=result1["messages"]
)
# Agent: "I need the service name"
# Or if context is clear: "Due 2026-11-22 (21 days from 2026-11-01)"
```

## Implementation Notes

### Why Dict-Based Graph?
The current LangGraph implementation (`app/graph.py`) uses a dict-based graph structure instead of importing the real `langgraph` library. This is intentional:

1. **No external dependency** - works out of the box
2. **Demonstrates concepts** - shows graph pattern without library complexity
3. **Easy to port** - structure mirrors real LangGraph, simple to upgrade

To use real LangGraph, uncomment in `requirements.txt`:
```txt
langgraph>=0.1.0
```

Then replace the graph creation with:
```python
from langgraph.graph import StateGraph, END

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("approval", approval_node)
graph.add_node("tools", tools_node)
graph.add_conditional_edges("agent", route_after_agent)
...
compiled = graph.compile()
```

### Working Days Calculation
The `_add_working_days` function in `app/tools.py` accounts for:
- **Weekends**: Saturday-Sunday skipped
- **Holidays**: Maharashtra-specific public holidays (2026-2027)

Example: 15 working days from 2026-11-01 (Monday):
- Calendar days: 2026-11-16 (15 days)
- Working days: 2026-11-21 (skips 2 weekends + Diwali on 2026-11-13)

### Approval Step
The approval node (`approval_node` in `app/graph.py`) currently auto-approves all tool calls with a console print. In production:

1. **Pause execution** after agent decides tool calls
2. **Send to user** via websocket/webhook
3. **Wait for response** (approve/reject/modify)
4. **Resume execution** based on decision

Implementation example:
```python
def approval_node(state: AgentState) -> AgentState:
    pending = state["pending_tool_calls"]
    # In production: send to approval queue
    approval_response = await approval_service.request_approval(pending)
    state["approval_status"] = approval_response.status
    return state
```

## Testing

```bash
# Test tools directly
python -c "from app.tools import rag_search; print(rag_search('time limit caste'))"
python -c "from app.tools import rts_due_date; print(rts_due_date('caste certificate', '2026-11-01'))"

# Test hand-written agent
python -m app.agent_loop "What is the time limit for caste certificate?"

# Test LangGraph agent
python -m app.graph "Is my caste certificate due if I applied on 2026-11-01?"

# Test API endpoint
curl -X POST http://127.0.0.1:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the time limit for caste certificate?"}'
```

---

**Implementation Status:** ✅ Complete (S1 + S2)  
**Date:** November 18, 2026  
**Files:**
- `app/tools.py` - RAG search + due date calculation tools
- `app/agent_loop.py` - Hand-written pattern-matching agent
- `app/graph.py` - LangGraph-style agent with memory + approval
- `app/main.py` - POST /agent endpoint added
