# Checkpoint 2: Streamlit UI with Appeal Ladder

**Date:** November 18, 2026  
**Tag:** `checkpoint-2`

## What's New

### Streamlit Chat Interface (`ui/app.py`)

Full-featured chat UI for AapleSeva with:

1. **Dual Endpoint Support**
   - RAG (Fast): Direct document search via POST /ask
   - Agent (Smart): Multi-step reasoning via POST /agent with conversation memory

2. **Source Citations**
   - Expandable source cards showing document title, page number
   - Relevance score for each source
   - Clean, readable format

3. **User Feedback**
   - Thumbs up/down buttons on every answer
   - Feedback saved to `ui/feedback.json` with timestamp
   - Statistics shown in sidebar (total thumbs up/down)

4. **🪜 Appeal Ladder (Signature Feature)**
   - Visual timeline calculator for RTS appeal process
   - 4 steps: Designated Officer → First Appellate → Second Appellate → RTS Commission
   - Each step shows:
     - Officer name and designation
     - Date the step opens
     - Filing deadline (30 days for appeals)
     - Decision deadline
     - Status indicator (⚪⚫🟢🟡🔴)
   - Calculates all dates from application date + service time limit
   - Color-coded status:
     - ⚪ Not yet open
     - 🟢 Service delivery on time
     - 🟡 Can file appeal
     - 🔴 Overdue or window closed

## File Structure

```
Training/
├── ui/
│   ├── app.py              # Streamlit chat interface (NEW)
│   └── feedback.json       # User feedback storage (generated)
├── docs/
│   └── screenshots/
│       ├── README.md       # Screenshot instructions (NEW)
│       └── streamlit-app.md # Screenshot placeholder (NEW)
├── app/
│   ├── tools.py           # RAG + due date tools
│   ├── agent_loop.py      # Hand-written agent
│   ├── graph.py           # LangGraph agent
│   ├── rag.py             # RAG system
│   └── main.py            # FastAPI with /ask and /agent
├── AGENT_SYSTEM.md        # Agent documentation
├── RAG_SYSTEM.md          # RAG documentation
├── README.md              # Updated with UI section
└── requirements.txt       # Added streamlit>=1.28.0
```

## Appeal Ladder Details

The appeal ladder implements the Maharashtra RTS Act appeal timeline:

1. **Designated Officer** - Service delivery
   - Due date: application_date + time_limit_days
   - Status: Green if on time, Red if overdue

2. **First Appellate Authority** - First level of appeal
   - Opens: On service due date (if not delivered)
   - Filing window: 30 days from due date
   - Decision due: 30 days from filing
   - Status: Yellow when filing window open

3. **Second Appellate Authority** - Second level of appeal
   - Opens: After first appellate decision
   - Filing window: 30 days from first decision
   - Decision due: 30 days from filing
   - Status: Yellow when filing window open

4. **RTS Commission** - Final state authority
   - Can approach: After second appellate decision
   - Final grievance redressal mechanism
   - Status: Yellow when accessible

## Running the Demo

```bash
# Terminal 1: Start backend
cd Training
python -m uvicorn app.main:app --reload

# Terminal 2: Start UI
streamlit run ui/app.py
# Opens at http://localhost:8501
```

## Example Usage

1. **Chat with RAG:**
   - Select "RAG (Fast)" in sidebar
   - Ask: "What is the time limit for caste certificate?"
   - Get answer with source citations
   - Click thumbs up/down

2. **Chat with Agent:**
   - Select "Agent (Smart)" in sidebar
   - Ask: "Is my water connection due if I applied on 2026-11-01?"
   - Agent calls rts_due_date tool
   - Returns calculated timeline

3. **Calculate Appeal Timeline:**
   - In sidebar "Appeal Ladder" section
   - Enter service: "water connection"
   - Enter date: 2026-11-01
   - Click "Calculate Timeline"
   - See full 4-step timeline with dates

## Technical Implementation

**Appeal Date Calculation:**
```python
# From application date and time limit
service_due = app_date + time_limit_days

# First appeal
first_appeal_opens = service_due
first_appeal_deadline = service_due + 30 days
first_decision_due = first_appeal_opens + 30 days

# Second appeal
second_appeal_opens = first_decision_due
second_appeal_deadline = first_decision_due + 30 days
second_decision_due = second_appeal_opens + 30 days

# RTS Commission
rts_commission = second_decision_due
```

**API Integration:**
- `call_ask_endpoint()` → POST /ask with question + top_k
- `call_agent_endpoint()` → POST /agent with query + conversation_history
- `get_service_by_name()` → GET /search to find service details

**Feedback Storage:**
```json
{
  "timestamp": "2026-11-18T10:30:00",
  "question": "What is the time limit...",
  "answer": "21 days [RTS Notified...]",
  "thumbs": "up",
  "endpoint": "ask"
}
```

## What's Complete

- ✅ Streamlit chat interface
- ✅ RAG and Agent endpoint integration
- ✅ Source citations with expandable cards
- ✅ Thumbs up/down feedback system
- ✅ Appeal ladder visualization
- ✅ 4-step timeline with officers and dates
- ✅ Color-coded status indicators
- ✅ Feedback statistics in sidebar
- ✅ Documentation and README update
- ✅ requirements.txt updated

## Known Limitations

1. **Screenshot pending**: Placeholder created, actual screenshot needs manual capture
2. **No session persistence**: Feedback saved but no user sessions
3. **Single conversation**: No multi-session history (chat resets on page refresh)
4. **Mock officer data**: Some services may show "Not specified" for officers

## Next Steps (Post-Checkpoint)

If extending this system:
1. Add screenshot to docs/screenshots/
2. Implement session management (store conversations)
3. Add export feature (download chat history)
4. Add service search/filter UI
5. Add appeal form generator (pre-fill based on timeline)
6. Deploy to cloud (Streamlit Community Cloud / Heroku)

---

**Status:** ✅ Checkpoint 2 Complete  
**Commit:** Pending user approval  
**Tag:** `checkpoint-2` (to be created on push)
