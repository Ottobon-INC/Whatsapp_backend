# modules/lead_manager.py
from datetime import datetime
from typing import Dict, Any, Optional

from supabase_client import supabase_insert, supabase_select, supabase_update

# Steps in the onboarding flow
STEP_NAME = "ask_name"
STEP_PHONE = "ask_phone"
STEP_AGE = "ask_age"
STEP_GENDER = "ask_gender"
STEP_PROBLEM = "ask_problem"
STEP_COMPLETE = "complete"

def _get_chat_state(user_id: str) -> dict:
    """Retrieve the chat state from sakhi_chat_states table."""
    try:
        rows = supabase_select("sakhi_chat_states", select="context", filters=f"user_id=eq.{user_id}")
        if rows and isinstance(rows, list) and len(rows) > 0:
            val = rows[0].get("context")
            # Ensure we return a dict, even if DB has None/null
            if val is None:
                return {}
            return val
    except Exception as e:
        print(f"Error fetching chat state: {e}")
        return {}
    return {}

def _update_chat_state(user_id: str, context: dict):
    """Update or insert the chat state in sakhi_chat_states table."""
    # Check if exists
    rows = supabase_select("sakhi_chat_states", select="user_id", filters=f"user_id=eq.{user_id}")
    if rows:
        match = f"user_id=eq.{user_id}"
        # We merge with existing context ideally, but here we can just overwrite or merge
        # For safety, let's fetch current, merge, and save
        current = _get_chat_state(user_id)
        current.update(context)
        return supabase_update("sakhi_chat_states", match, {"context": current})
    else:
        return supabase_insert("sakhi_chat_states", {"user_id": user_id, "context": context})

def handle_lead_flow(user_id: str, message: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle the conversational flow for adding a new lead.
    Returns the response payload (reply, mode, etc.).
    """
    message = message.strip()
    
    # Use separate table for state
    context = _get_chat_state(user_id)
    lead_state = context.get("lead_flow") or {}
    
    current_step = lead_state.get("step")
    temp_data = lead_state.get("data", {})

    # Initial Trigger: /newlead
    if message.lower() == "/newlead":
        # Initialize flow
        new_state = {
            "lead_flow": {
                "step": STEP_NAME,
                "data": {}
            }
        }
        _update_chat_state(user_id, new_state)
        return {
            "reply": "Hello! I'm here to help you register a new patient. Let's start with their name. What should we call them?",
            "mode": "lead_input"
        }

    # If we are not in a step (shouldn't happen if called correctly from main), reset
    if not current_step:
         return {
            "reply": "I'm sorry, I lost track. Please type /newlead to start again.",
            "mode": "general"
        }

    # State Machine
    reply_text = ""
    next_step = current_step
    
    if current_step == STEP_NAME:
        # User provided Name
        temp_data["name"] = message
        next_step = STEP_PHONE
        reply_text = f"Thanks. Could you share {message}'s phone number so we can reach out?"
    
    elif current_step == STEP_PHONE:
        # User provided Phone
        temp_data["phone"] = message
        next_step = STEP_AGE
        reply_text = "Got it. May I ask how old they are?"
        
    elif current_step == STEP_AGE:
        # User provided Age
        temp_data["age"] = message
        next_step = STEP_GENDER
        reply_text = "And their gender?"
        
    elif current_step == STEP_GENDER:
        # User provided Gender
        temp_data["gender"] = message
        next_step = STEP_PROBLEM
        reply_text = "Finally, could you briefly tell me what health concern or problem they are facing? Take your time."

    elif current_step == STEP_PROBLEM:
        # User provided Problem -> FINISH
        temp_data["problem"] = message
        
        # Save to DB
        try:
            _save_lead_to_db(temp_data, user_id)
            reply_text = "Thank you. I've noted everything down. We'll take good care of them."
            
            # Clear context
            _update_chat_state(user_id, {"lead_flow": None})  # Remove flow state
            return {
                "reply": reply_text,
                "mode": "lead_complete"
            }
        except Exception as e:
            print(f"Error saving lead: {e}")
            return {
                "reply": "I encountered an error saving the lead. Please try again later.",
                "mode": "error"
            }
            
    # Update State for intermediate steps
    _update_chat_state(user_id, {
        "lead_flow": {
            "step": next_step,
            "data": temp_data
        }
    })
    
    return {
        "reply": reply_text,
        "mode": "lead_input"
    }


def _save_lead_to_db(data: Dict[str, str], added_by_user_id: str):
    # Using user provided schema columns
    # Table: sakhi_clinic_leads
    # Columns: name, phone, age, gender, problem, status, assigned_to_user_id
    payload = {
        "name": data.get("name"),
        "phone": data.get("phone"),
        "age": data.get("age"),
        "gender": data.get("gender"),
        "problem": data.get("problem"),
        "status": "New Inquiry",
        "source": "Whatsapp-Sakhi",
        # "assigned_to_user_id": added_by_user_id, # Removed to avoid FK violation if user is not in sakhi_clinic_users
    }
    return supabase_insert("sakhi_clinic_leads", payload)
