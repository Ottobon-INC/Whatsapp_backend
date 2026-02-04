# implementation_plan.md

# Goal: Clinic Lead Onboarding Flow

Implement a conversational flow triggered by `/newlead` to collect clinic lead details (Name, Phone, Age, Gender, Problem) with an empathetic tone, storing the data in `sakhi_clinic_leads`.

## User Review Required

> [!IMPORTANT]
> **Table Name Clarity**: The user mentioned `sakhi_clinic_users` but the provided screenshot shows `sakhi_clinic_leads`. I will proceed with `sakhi_clinic_leads` as the table name.

> [!NOTE]
> **Empathy First**: The bot will ask one question at a time using gentle language, avoiding a robotic form-filling feel.

## Proposed Changes

### Database
#### [NEW] [setup_leads.sql](file:///d:/Ottobon/Sakhi-Whatsapp-Backend/setup_leads.sql)
- Create `sakhi_clinic_leads` table if it doesn't exist.
- Columns: `id, name, phone, age, gender, problem, status, date_added`.

### Backend Logic

#### [MODIFY] [main.py](file:///d:/Ottobon/Sakhi-Whatsapp-Backend/main.py)
- **Intercept `/newlead`**: Check if the message starts with `/newlead` (or is exactly that).
- **State Management**: Introduce a "lead_onboarding" mode in the response payload or manage state via `user_profile` updates.
    - We will add a `context` JSONB column to `sakhi_users` (via `setup_leads.sql`) to track the current flow state (e.g., `{"active_flow": "lead_capture", "step": "ask_name", "temp_data": {...}}`).
- **Flow**:
    1.  User types `/newlead`.
    2.  Sakhi: "Hello! I'm here to help you register a new patient. Let's start with their name. What should we call them?"
    3.  User: "John Doe"
    4.  Sakhi: "Thanks. Could you share their phone number so we can reach out?"
    5.  User: "1234567890" (Validate phone)
    6.  Sakhi: "Got it. May I ask how old they are?"
    7.  User: "30"
    8.  Sakhi: "And their gender?"
    9.  User: "Male"
    10. Sakhi: "Finally, could you briefly tell me what health concern or problem they are facing? Take your time."
    11. User: "Fever and headaches"
    12. Sakhi: "Thank you. I've noted everything down. We'll take good care of them." -> **INSERT into DB**.

#### [NEW] [modules/lead_manager.py](file:///d:/Ottobon/Sakhi-Whatsapp-Backend/modules/lead_manager.py)
- `handle_lead_flow(user_id, message, user_context)`: Main handler function.
- `create_lead(data)`: Insert into `sakhi_clinic_leads`.

## Verification Plan

### Manual Verification
- Run `trigger_chat.py` with `/newlead`.
- Verify `sakhi_clinic_leads` has the new row.
