-- Supabase PostgreSQL Schema for AI Fitness Coach (SIH26196)
-- Hard Privacy Guarantee: NO video, image, or raw frame data is ever stored.

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) DEFAULT 'Athlete',
    age INT NOT NULL,
    height FLOAT NOT NULL, -- in cm
    weight FLOAT NOT NULL, -- in kg
    biological_sex VARCHAR(10) NOT NULL, -- 'male' or 'female'
    goal VARCHAR(20) NOT NULL, -- 'weight_loss', 'maintenance', 'muscle_gain'
    activity_level VARCHAR(20) DEFAULT 'moderate', -- 'sedentary', 'light', 'moderate', 'active', 'very_active'
    bmi FLOAT,
    target_calories INT,
    nutrition_plan JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workout_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    exercise_type VARCHAR(50) NOT NULL, -- 'squats', 'pushups', 'bicep_curls'
    reps INT NOT NULL DEFAULT 0,
    form_score FLOAT DEFAULT 100.0,
    fatigue_triggers INT DEFAULT 0,
    duration_seconds INT DEFAULT 0,
    details JSONB, -- stores per-rep timestamps & scores (numeric data only)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS routines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    environment VARCHAR(20) NOT NULL, -- 'home' or 'gym'
    exercises JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
