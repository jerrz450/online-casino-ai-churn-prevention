
-- Player profiles
CREATE TABLE players (
    player_id INT PRIMARY KEY,
    player_type VARCHAR(20),
    ltv DECIMAL(10, 2),
    created_at TIMESTAMPTZ,
    last_active TIMESTAMPTZ
);

-- Monitor decisions
CREATE TABLE monitor_events (      
    id UUID PRIMARY KEY,
    player_id INT REFERENCES players(player_id),
    timestamp TIMESTAMPTZ,
    decision VARCHAR(10),
    decision_source VARCHAR(50),
    player_context JSONB,
    processing_time_ms INT
  );

  -- Predictor results
  CREATE TABLE predictor_results (
      id UUID PRIMARY KEY,
      player_id INT REFERENCES players(player_id),
      timestamp TIMESTAMPTZ,
      risk_score DECIMAL(3,2),
      similar_count INT,
      churned_count INT,
      similar_player_ids INT[],
      actual_outcome VARCHAR(20),
      prediction_correct BOOLEAN
  );

  -- Interventions
 CREATE TABLE interventions (

    id UUID PRIMARY KEY,
    player_id INT REFERENCES players(player_id),                                                                                                                                                                 
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    risk_score DECIMAL(3,2),                                                                                                                                                                                     
    intervention_type VARCHAR(50),
    amount DECIMAL(10,2),
    message TEXT,
    outcome VARCHAR(20),
    outcome_measured_at TIMESTAMPTZ

  );

  -- Player communication preferences
  CREATE TABLE player_preferences (
      player_id INT PRIMARY KEY REFERENCES players(player_id),
      email_ok BOOLEAN DEFAULT true,
      sms_ok BOOLEAN DEFAULT true,
      push_ok BOOLEAN DEFAULT true,
      language VARCHAR(10) DEFAULT 'en',
      do_not_disturb BOOLEAN DEFAULT false,
      opted_out_marketing BOOLEAN DEFAULT false,
      monthly_bonus_total DECIMAL(10,2) DEFAULT 0,
      last_intervention_at TIMESTAMPTZ
  );

  -- Monthly bonus tracking (compliance)
  CREATE TABLE bonus_tracking (
      player_id INT REFERENCES players(player_id),
      month DATE,
      total_bonus_amount DECIMAL(10,2),
      PRIMARY KEY (player_id, month)
  );

  -- Self-exclusion list
  CREATE TABLE exclusions (
      player_id INT PRIMARY KEY REFERENCES players(player_id),
      excluded_at TIMESTAMPTZ,
      excluded_until TIMESTAMPTZ,
      reason VARCHAR(100)
  );