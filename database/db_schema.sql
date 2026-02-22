-- Player profiles
CREATE TABLE players (
    player_id INT PRIMARY KEY,
    player_type VARCHAR(20),
    ltv DECIMAL(10, 2),
    created_at TIMESTAMPTZ,
    last_active TIMESTAMPTZ
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

-- Interventions (offers, bonuses sent to at-risk players)
CREATE TABLE interventions (
    id UUID PRIMARY KEY,
    player_id INT REFERENCES players(player_id),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    risk_score DECIMAL(3,2),
    intervention_type VARCHAR(50),
    amount DECIMAL(10,2),
    message TEXT,
    model_version VARCHAR(50),
    feature_timestamp TIMESTAMPTZ,
    outcome VARCHAR(20),
    outcome_measured_at TIMESTAMPTZ
);

-- Monthly bonus tracking (compliance)
CREATE TABLE bonus_tracking (
    player_id INT REFERENCES players(player_id),
    month DATE,
    total_bonus_amount DECIMAL(10,2),
    PRIMARY KEY (player_id, month)
);

-- Self-exclusion list (responsible gaming)
CREATE TABLE exclusions (
    player_id INT PRIMARY KEY REFERENCES players(player_id),
    excluded_at TIMESTAMPTZ,
    excluded_until TIMESTAMPTZ,
    reason VARCHAR(100)
);

-- ─── Training Pipeline ───────────────────────────────────────────────────────

-- Raw event stream captured during simulator training runs
CREATE TABLE raw_training_events (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    player_id INT REFERENCES players(player_id),
    event_type VARCHAR(20) NOT NULL,
    payload JSONB NOT NULL,
    received_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_raw_training_events_run_id ON raw_training_events(run_id);
CREATE INDEX idx_raw_training_events_player_id ON raw_training_events(player_id, received_at);

-- Session-end feature snapshots — Feast offline store + XGBoost training dataset
-- event_timestamp and created are required by Feast for point-in-time correct joins
CREATE TABLE player_session_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL,
    player_id INT REFERENCES players(player_id),
    player_type VARCHAR(20),
    session_number INT,

    -- Feast required timestamps
    event_timestamp TIMESTAMPTZ NOT NULL,
    created TIMESTAMPTZ DEFAULT NOW(),

    -- Features (mirrors PlayerBehaviorState at session end)
    emotional_state INT,                  -- 0=neutral,1=winning,2=tilting,3=bored,4=recovering
    consecutive_losses INT,
    consecutive_wins INT,
    session_loss_pct FLOAT,               -- (session_start_bankroll - current) / session_start
    bankroll_pct_remaining FLOAT,         -- current_bankroll / typical_bankroll
    win_rate FLOAT,                       -- wins / bets_this_session
    avg_bet_ratio FLOAT,                  -- avg_bet / typical_bet
    sessions_completed INT,
    bets_in_session INT,
    sessions_since_last_big_event INT,
    is_at_risk BOOLEAN,
    net_profit_loss_normalized FLOAT,     -- net_pnl / total_wagered
    interventions_received INT,

    -- Label (set by prepare.py after simulation completes)
    churned SMALLINT,                     -- NULL=pending, 0=retained, 1=churned
    labeled_at TIMESTAMPTZ
);

CREATE INDEX idx_snapshots_player_id ON player_session_snapshots(player_id, event_timestamp);
CREATE INDEX idx_snapshots_run_id ON player_session_snapshots(run_id);
CREATE INDEX idx_snapshots_unlabeled ON player_session_snapshots(run_id) WHERE churned IS NULL;

-- ─── Online Decisioning ──────────────────────────────────────────────────────

-- XGBoost decision log (audit trail for every real-time decision)
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id INT REFERENCES players(player_id),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    churn_score FLOAT NOT NULL,
    model_version VARCHAR(50),
    feature_timestamp TIMESTAMPTZ,        -- freshness of features used
    action VARCHAR(50),                   -- 'no_action', 'offer_sent', 'rg_flag'
    reason TEXT
);

CREATE INDEX idx_decisions_player_id ON decisions(player_id, timestamp);
