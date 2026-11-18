# AapleSeva Streamlit UI Screenshot

**To generate the actual screenshot:**

1. Start the FastAPI backend:
   ```bash
   cd Training
   python -m uvicorn app.main:app --reload
   ```

2. Start the Streamlit UI:
   ```bash
   streamlit run ui/app.py
   ```

3. In the UI:
   - In the sidebar "Appeal Ladder" section, enter:
     - Service name: "water connection"
     - Application date: 2026-11-01
     - Click "Calculate Timeline"
   
   - In the chat, ask: "What is the time limit for water connection?"

4. Take a full-page screenshot showing:
   - Left sidebar with settings and appeal calculator
   - Main chat area with question and answer
   - Appeal ladder visualization at the bottom showing all 4 steps

5. Save as `streamlit-app.png` in this directory

---

## Expected Screenshot Content

**Sidebar shows:**
- Radio buttons: RAG (Fast) / Agent (Smart)
- Appeal Ladder calculator form
- Feedback statistics (thumbs up/down)

**Main area shows:**
- Chat messages with expandable source citations
- Thumbs up/down buttons below answers

**Appeal Ladder shows:**
- 🟢 Step 1: Designated Officer (Executive Engineer) - Service Due: 2026-11-16
- ⚪ Step 2: First Appellate (Superintending Engineer) - Opens: 2026-11-16
- ⚪ Step 3: Second Appellate (Chief Engineer) - Opens: 2026-12-16
- ⚪ Step 4: RTS Commission - Can approach: 2027-01-15

With status legend: ⚪ Not yet open | 🟢 On time | 🟡 Can appeal | 🔴 Overdue
