-- Create the table for clinic leads
create table if not exists sakhi_clinic_leads (
    id uuid default gen_random_uuid() primary key,
    name text,
    phone text,
    age text,
    gender text,
    problem text,
    status text default 'New Inquiry',
    assigned_to_user uuid, -- Optional: link to the user who added the lead
    date_added timestamptz default now(),
    updated_at timestamptz default now()
);

-- Add context column to sakhi_users if it doesn't exist
-- This field will store temporary state for multi-turn conversations (like lead onboarding)
alter table sakhi_users 
add column if not exists context jsonb default '{}'::jsonb;
