# Walkthrough: Clinic Lead Onboarding (Strict Schema)

I have implemented the **Lead Onboarding** feature which allows you to register new clinic leads via Sakhi chat using the `/newlead` command.

## 🚀 Key Improvements
- **Strict Schema Compliance**: The `sakhi_clinic_leads` table exactly matches your provided SQL.
- **No Schema Changes to `sakhi_users`**: Conversation state is now stored in a separate table: `sakhi_chat_states`.
- **New Command**: `/newlead` triggers an empathetic interview flow.
- **Data Collections**: Collects Name, Phone, Age, Gender, and Problem step-by-step.

## 🛠️ Setup Required (Important!)

Before testing, you **MUST** update your database schema using the new strict script.

1.  Open your Supabase SQL Editor.
2.  Copy the contents of `setup_leads_strict.sql`.
3.  Run the script to create `sakhi_clinic_leads` and `sakhi_chat_states`.
4.  **Note**: If you already ran the previous script, this is safe to run (it uses `if not exists`), but you might want to drop `sakhi_clinic_leads` first if the columns were different.

## 🧪 How to Test

1.  Start your backend server:
    ```bash
    uvicorn main:app --reload
    ```
2.  Send a message `/newlead` to the bot.
3.  Follow the conversation flow:
    - Bot: "What should we call them?"
    - You: "John Doe"
    - Bot: "Phone number?"
    - ... and so on.

## 📁 Files Created/Modified
- `setup_leads_strict.sql`: STRICT database schema (User defined keys).
- `modules/lead_manager.py`: Bot logic using `sakhi_chat_states`.
- `modules/user_profile.py`: No longer used for context storage.
- `main.py`: Connected the new flow using separate state lookup.
