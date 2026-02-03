-- Create the dedicated table for encrypted chat storage
create table if not exists sakhi_encrypted_chats (
  id uuid default gen_random_uuid() primary key,
  user_id text not null,
  role text not null,        -- 'user' or 'sakhi'
  ciphertext text not null,  -- Base64 encoded encrypted content
  nonce text not null,       -- Base64 encoded nonce (12 bytes)
  language text default 'en',
  created_at timestamptz default now()
);

-- Index for faster history retrieval
create index if not exists idx_enc_chats_user on sakhi_encrypted_chats(user_id);

-- Optional: Enable RLS
alter table sakhi_encrypted_chats enable row level security;
create policy "Enable all access" on sakhi_encrypted_chats for all using (true) with check (true);
