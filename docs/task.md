# Tasks

- [x] Explore codebase for recent changes
- [x] Brainstorm features with user
- [x] Create implementation plan for approved features
    - [x] Plan Lead Onboarding Flow (/newlead)
- [x] Implement Lead Onboarding (Refining)
    - [x] Create `setup_leads_strict.sql` with user's schema & separate state table
    - [x] Update `lead_manager.py` to use new columns (`assigned_to_user_id`)
    - [x] Update `user_profile.py` / `lead_manager.py` to use `sakhi_chat_states`
    - [x] Verify Lead Onboarding
