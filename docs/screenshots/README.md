# Screenshots

## streamlit-app.png

Screenshot of the AapleSeva Streamlit UI showing:

**Left sidebar:**
- Endpoint selection (RAG/Agent radio buttons)
- Appeal Ladder calculator form (service name + application date)
- Feedback statistics (thumbs up/down counts)

**Main chat area:**
- Chat messages with user questions and assistant answers
- Expandable "Sources" cards showing document citations
- Thumbs up/down feedback buttons below each answer

**Appeal Ladder visualization (below chat):**
Shows 4-step timeline for a water connection service:

1. 🟢 **Step 1: Designated Officer** 
   - *Executive Engineer In Charge of Water Works*
   - Service Due: 2026-11-16
   - ✓ 14 days remaining

2. ⚪ **Step 2: First Appellate Authority**
   - *Superintending Engineer*
   - Opens: 2026-11-16
   - File by: 2026-12-16 (30 days)
   - Decision due: 2026-12-16

3. ⚪ **Step 3: Second Appellate Authority**
   - *Chief Engineer*
   - Opens: 2026-12-16
   - File by: 2027-01-15 (30 days)
   - Decision due: 2027-01-15

4. ⚪ **Step 4: Maharashtra RTS Commission**
   - *State-level appellate body*
   - Can approach: 2027-01-15
   - Final authority for grievance redressal

**Status Legend:** ⚪ Not yet open | 🟢 On time | 🟡 Can appeal | 🔴 Overdue

---

**To generate actual screenshot:**
1. Start backend: `python -m uvicorn app.main:app --reload`
2. Start UI: `streamlit run ui/app.py`
3. In sidebar: Enter "water connection" and date "2026-11-01", click Calculate
4. In chat: Ask "What is the time limit for water connection?"
5. Take full-page screenshot showing chat + appeal ladder
6. Save as `streamlit-app.png` in this directory
