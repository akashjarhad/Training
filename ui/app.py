"""
ui/app.py
Streamlit chat interface for AapleSeva with appeal ladder visualization.

Features:
- Chat interface calling /ask (RAG) or /agent (agentic) endpoints
- Source citations with expandable details
- Thumbs up/down feedback saved to feedback.json
- Appeal Ladder: Visual timeline showing Designated Officer → First Appellate →
  Second Appellate → RTS Commission with dates each step opens

Run:
    streamlit run ui/app.py
"""

import json
import requests
import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


# Configuration
API_BASE_URL = "http://127.0.0.1:8000"
FEEDBACK_FILE = Path(__file__).parent / "feedback.json"

# Appeal timeline constants (days)
FIRST_APPEAL_AFTER_DAYS = 30  # File 1st appeal within 30 days of due date
FIRST_APPEAL_DECISION_DAYS = 30  # 1st appellate has 30 days to decide
SECOND_APPEAL_AFTER_DAYS = 30  # File 2nd appeal within 30 days of 1st decision
SECOND_APPEAL_DECISION_DAYS = 30  # 2nd appellate has 30 days to decide
RTS_COMMISSION_AFTER_DAYS = 60  # Approach RTS Commission after 60 days


# ============================================================================
# API Calls
# ============================================================================

def call_ask_endpoint(question: str, top_k: int = 5) -> dict:
    """Call POST /ask (RAG endpoint)."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/ask",
            json={"question": question, "top_k": top_k},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": str(exc), "answer": f"Error: {exc}"}


def call_agent_endpoint(query: str, conversation_history: list = None) -> dict:
    """Call POST /agent (LangGraph agent endpoint)."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/agent",
            json={
                "query": query,
                "conversation_history": conversation_history or []
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": str(exc), "answer": f"Error: {exc}"}


def get_service_by_name(service_name: str) -> dict | None:
    """Fetch service details from API."""
    try:
        # Search for service
        response = requests.get(
            f"{API_BASE_URL}/search",
            params={"q": service_name, "top_k": 1},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        return results[0] if results else None
    except Exception:
        return None


# ============================================================================
# Feedback Storage
# ============================================================================

def save_feedback(question: str, answer: str, thumbs: str, endpoint: str):
    """Save user feedback to JSON file."""
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing feedback
    if FEEDBACK_FILE.exists():
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            feedback_data = json.load(f)
    else:
        feedback_data = []
    
    # Append new feedback
    feedback_data.append({
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "answer": answer[:200],  # Truncate for storage
        "thumbs": thumbs,  # "up" or "down"
        "endpoint": endpoint,  # "ask" or "agent"
    })
    
    # Save
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(feedback_data, f, indent=2, ensure_ascii=False)


# ============================================================================
# Appeal Ladder
# ============================================================================

def calculate_appeal_dates(
    application_date: str,
    time_limit_days: int
) -> dict[str, str]:
    """
    Calculate appeal timeline dates.
    
    Returns dict with:
        - service_due: When service should be delivered
        - first_appeal_opens: When 1st appeal can be filed
        - first_appeal_deadline: Last day to file 1st appeal
        - first_decision_due: When 1st appellate must decide
        - second_appeal_opens: When 2nd appeal can be filed
        - second_appeal_deadline: Last day to file 2nd appeal
        - second_decision_due: When 2nd appellate must decide
        - rts_commission: When RTS Commission can be approached
    """
    try:
        app_date = datetime.fromisoformat(application_date).date()
    except ValueError:
        app_date = datetime.strptime(application_date, "%Y-%m-%d").date()
    
    # Service delivery due date
    service_due = app_date + timedelta(days=time_limit_days)
    
    # First appeal opens on due date if service not provided
    first_appeal_opens = service_due
    first_appeal_deadline = service_due + timedelta(days=FIRST_APPEAL_AFTER_DAYS)
    
    # First appellate authority must decide within 30 days
    first_decision_due = first_appeal_opens + timedelta(days=FIRST_APPEAL_DECISION_DAYS)
    
    # Second appeal opens after first decision (if unfavorable)
    second_appeal_opens = first_decision_due
    second_appeal_deadline = first_decision_due + timedelta(days=SECOND_APPEAL_AFTER_DAYS)
    
    # Second appellate authority must decide within 30 days
    second_decision_due = second_appeal_opens + timedelta(days=SECOND_APPEAL_DECISION_DAYS)
    
    # RTS Commission can be approached after exhausting appeals
    rts_commission = second_decision_due
    
    return {
        "service_due": service_due.isoformat(),
        "first_appeal_opens": first_appeal_opens.isoformat(),
        "first_appeal_deadline": first_appeal_deadline.isoformat(),
        "first_decision_due": first_decision_due.isoformat(),
        "second_appeal_opens": second_appeal_opens.isoformat(),
        "second_appeal_deadline": second_appeal_deadline.isoformat(),
        "second_decision_due": second_decision_due.isoformat(),
        "rts_commission": rts_commission.isoformat(),
    }


def render_appeal_ladder(service: dict, application_date: str):
    """
    Render the Appeal Ladder visualization.
    
    Shows 4 steps with officers and dates:
    1. Designated Officer (service delivery)
    2. First Appellate Authority
    3. Second Appellate Authority
    4. RTS Commission
    """
    st.markdown("---")
    st.subheader("📋 Appeal Ladder")
    st.caption("Timeline for appeals under the Maharashtra Right to Service Act")
    
    time_limit = service.get("time_limit_days")
    if not time_limit:
        st.warning("Time limit not available for this service")
        return
    
    # Calculate dates
    dates = calculate_appeal_dates(application_date, time_limit)
    today = datetime.now().date()
    
    # Service info
    st.markdown(f"**Service:** {service.get('service_name', 'Unknown')}")
    st.markdown(f"**Department:** {service.get('department', 'Unknown')}")
    st.markdown(f"**Time Limit:** {time_limit} days")
    st.markdown(f"**Application Date:** {application_date}")
    
    st.markdown("")
    
    # Step 1: Designated Officer
    service_due = datetime.fromisoformat(dates["service_due"]).date()
    is_past_due = today > service_due
    
    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            if is_past_due:
                st.markdown("🔴 **Step 1**")
            else:
                st.markdown("🟢 **Step 1**")
        with col2:
            st.markdown("**Designated Officer**")
            officer = service.get("designated_officer", "Not specified")
            st.markdown(f"*{officer}*")
            st.markdown(f"**Service Due:** {dates['service_due']}")
            
            if is_past_due:
                days_late = (today - service_due).days
                st.markdown(f"⚠️ <span style='color: red;'>OVERDUE by {days_late} days</span>", unsafe_allow_html=True)
            else:
                days_remaining = (service_due - today).days
                st.markdown(f"✓ {days_remaining} days remaining")
    
    st.markdown("")
    
    # Step 2: First Appellate Authority
    first_appeal_deadline = datetime.fromisoformat(dates["first_appeal_deadline"]).date()
    can_file_first = today >= service_due
    
    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            if can_file_first and today <= first_appeal_deadline:
                st.markdown("🟡 **Step 2**")
            elif today > first_appeal_deadline:
                st.markdown("🔴 **Step 2**")
            else:
                st.markdown("⚪ **Step 2**")
        with col2:
            st.markdown("**First Appellate Authority**")
            first_officer = service.get("first_appellate_officer", "Not specified")
            st.markdown(f"*{first_officer}*")
            st.markdown(f"**Opens:** {dates['first_appeal_opens']}")
            st.markdown(f"**File by:** {dates['first_appeal_deadline']} (30 days)")
            st.markdown(f"**Decision due:** {dates['first_decision_due']}")
            
            if can_file_first and today <= first_appeal_deadline:
                st.markdown("📝 You can file first appeal now")
            elif today > first_appeal_deadline:
                st.markdown("⏰ First appeal window closed")
    
    st.markdown("")
    
    # Step 3: Second Appellate Authority
    first_decision_due = datetime.fromisoformat(dates["first_decision_due"]).date()
    second_appeal_deadline = datetime.fromisoformat(dates["second_appeal_deadline"]).date()
    can_file_second = today >= first_decision_due
    
    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            if can_file_second and today <= second_appeal_deadline:
                st.markdown("🟡 **Step 3**")
            elif today > second_appeal_deadline:
                st.markdown("🔴 **Step 3**")
            else:
                st.markdown("⚪ **Step 3**")
        with col2:
            st.markdown("**Second Appellate Authority**")
            second_officer = service.get("second_appellate_officer", "District Collector / Department Head")
            st.markdown(f"*{second_officer}*")
            st.markdown(f"**Opens:** {dates['second_appeal_opens']}")
            st.markdown(f"**File by:** {dates['second_appeal_deadline']} (30 days)")
            st.markdown(f"**Decision due:** {dates['second_decision_due']}")
            
            if can_file_second and today <= second_appeal_deadline:
                st.markdown("📝 You can file second appeal now")
            elif today > second_appeal_deadline:
                st.markdown("⏰ Second appeal window closed")
    
    st.markdown("")
    
    # Step 4: RTS Commission
    rts_commission_date = datetime.fromisoformat(dates["rts_commission"]).date()
    can_approach_commission = today >= rts_commission_date
    
    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            if can_approach_commission:
                st.markdown("🟡 **Step 4**")
            else:
                st.markdown("⚪ **Step 4**")
        with col2:
            st.markdown("**Maharashtra RTS Commission**")
            st.markdown("*State-level appellate body*")
            st.markdown(f"**Can approach:** {dates['rts_commission']}")
            st.markdown("Final authority for grievance redressal")
            
            if can_approach_commission:
                st.markdown("📝 You can approach RTS Commission now")
    
    st.markdown("---")
    st.caption("⚪ Not yet open  |  🟢 On time  |  🟡 Can appeal  |  🔴 Overdue/Window closed")


# ============================================================================
# Main App
# ============================================================================

def main():
    st.set_page_config(
        page_title="AapleSeva Assistant",
        page_icon="🏛️",
        layout="wide",
    )
    
    st.title("🏛️ AapleSeva - Right to Service Assistant")
    st.caption("Maharashtra Right to Public Services Act, 2015")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Settings")
        
        endpoint_choice = st.radio(
            "Select Endpoint",
            options=["RAG (Fast)", "Agent (Smart)"],
            help="RAG: Direct document search. Agent: Multi-step reasoning with tools."
        )
        
        if endpoint_choice == "RAG (Fast)":
            top_k = st.slider("Number of sources", 1, 10, 5)
        
        st.markdown("---")
        
        st.header("🪜 Appeal Ladder")
        st.markdown("Calculate appeal timeline for any service")
        
        with st.form("appeal_form"):
            service_query = st.text_input(
                "Service name",
                placeholder="e.g., caste certificate, water connection"
            )
            app_date = st.date_input(
                "Application date",
                value=datetime.now().date()
            )
            calc_appeal = st.form_submit_button("Calculate Timeline")
        
        if calc_appeal and service_query:
            service = get_service_by_name(service_query)
            if service:
                st.session_state["show_appeal_ladder"] = True
                st.session_state["appeal_service"] = service
                st.session_state["appeal_app_date"] = app_date.isoformat()
            else:
                st.error("Service not found")
        
        st.markdown("---")
        
        # Feedback stats
        if FEEDBACK_FILE.exists():
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                feedback = json.load(f)
            thumbs_up = sum(1 for f in feedback if f.get("thumbs") == "up")
            thumbs_down = sum(1 for f in feedback if f.get("thumbs") == "down")
            st.metric("👍 Thumbs Up", thumbs_up)
            st.metric("👎 Thumbs Down", thumbs_down)
    
    # Main chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display existing messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # Show sources if available
            if msg.get("sources"):
                with st.expander("📚 Sources"):
                    for i, src in enumerate(msg["sources"], 1):
                        st.markdown(f"**{i}. {src.get('title', 'Unknown')}**")
                        if src.get('page'):
                            st.caption(f"Page {src['page']}")
                        st.caption(f"Relevance: {1 - src.get('distance', 0):.2%}")
                        st.markdown("---")
            
            # Show feedback buttons if assistant message
            if msg["role"] == "assistant" and not msg.get("feedback_given"):
                col1, col2, col3 = st.columns([1, 1, 8])
                with col1:
                    if st.button("👍", key=f"up_{msg.get('id')}"):
                        save_feedback(
                            msg.get("question", ""),
                            msg["content"],
                            "up",
                            msg.get("endpoint", "ask")
                        )
                        msg["feedback_given"] = True
                        st.rerun()
                with col2:
                    if st.button("👎", key=f"down_{msg.get('id')}"):
                        save_feedback(
                            msg.get("question", ""),
                            msg["content"],
                            "down",
                            msg.get("endpoint", "ask")
                        )
                        msg["feedback_given"] = True
                        st.rerun()
    
    # Chat input
    if prompt := st.chat_input("Ask about RTS services, time limits, appeals..."):
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response based on endpoint choice
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if endpoint_choice == "RAG (Fast)":
                    result = call_ask_endpoint(prompt, top_k=top_k)
                    endpoint_used = "ask"
                else:
                    # Build conversation history for agent
                    history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages[:-1]  # Exclude current prompt
                    ]
                    result = call_agent_endpoint(prompt, history)
                    endpoint_used = "agent"
                
                answer = result.get("answer", "No answer received")
                sources = result.get("sources", [])
                
                st.markdown(answer)
                
                # Show sources
                if sources:
                    with st.expander("📚 Sources"):
                        for i, src in enumerate(sources, 1):
                            st.markdown(f"**{i}. {src.get('title', 'Unknown')}**")
                            if src.get('page'):
                                st.caption(f"Page {src['page']}")
                            st.caption(f"Relevance: {1 - src.get('distance', 0):.2%}")
                            st.markdown("---")
                
                # Store assistant message
                msg_id = len(st.session_state.messages)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "question": prompt,
                    "endpoint": endpoint_used,
                    "id": msg_id,
                    "feedback_given": False
                })
                
                st.rerun()
    
    # Show appeal ladder if requested
    if st.session_state.get("show_appeal_ladder"):
        render_appeal_ladder(
            st.session_state["appeal_service"],
            st.session_state["appeal_app_date"]
        )


if __name__ == "__main__":
    main()
