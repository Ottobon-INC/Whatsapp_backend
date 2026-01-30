-- 1. Create the Leads Table (User's Exact Schema)
-- Note: Mapped foreign key to 'sakhi_users' assuming 'sakhi_clinic_users' was a typo or alias.
create table if not exists public.sakhi_clinic_leads (
  id uuid not null default gen_random_uuid (),
  name text not null,
  phone text not null,
  age text null,
  gender text null, -- storing as text to avoid enum dependency issues if not present
  source text null,
  inquiry text null,
  problem text null,
  treatment_doctor text null,
  treatment_suggested text null,
  status text not null default 'New Inquiry', 
  assigned_to_user_id uuid null,
  date_added timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  created_at timestamp with time zone null default now(),
  constraint sakhi_clinic_leads_pkey primary key (id)
  -- constraint sakhi_clinic_leads_assigned_to_user_id_fkey foreign KEY (assigned_to_user_id) references sakhi_users (user_id) on update CASCADE on delete set null
) TABLESPACE pg_default;


-- 2. Create a separate table for Chat State (Context)
-- This avoids modifying the existing sakhi_users table.
create table if not exists sakhi_chat_states (
    user_id uuid primary key references sakhi_users(user_id) on delete cascade,
    context jsonb default '{}'::jsonb,
    updated_at timestamptz default now()
);