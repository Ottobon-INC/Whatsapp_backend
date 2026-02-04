-- setup_rewards.sql
-- Migration script for Reward Management System

-- 1. Add rewards column to sakhi_users table
ALTER TABLE sakhi_users ADD COLUMN IF NOT EXISTS rewards INTEGER DEFAULT 0;

-- 2. Create table to store novel/new questions for future KB expansion
CREATE TABLE IF NOT EXISTS sakhi_new_questions (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    question TEXT NOT NULL,
    similarity_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for efficient user-based queries
CREATE INDEX IF NOT EXISTS idx_new_questions_user_id ON sakhi_new_questions(user_id);

-- Verify the column was added
-- SELECT column_name, data_type, column_default 
-- FROM information_schema.columns 
-- WHERE table_name = 'sakhi_users' AND column_name = 'rewards';
