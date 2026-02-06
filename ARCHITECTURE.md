# Casino Churn Detection - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│ SIMULATION LAYER (What we built)                   │
│ - PlayerSimulator: Generates 100 players, bets      │
│ - BehaviorModels: Tracks emotional state, streaks  │
│ - PlayerContextSerializer: Formats data for agents │
└─────────────────────────────────────────────────────┘
                        ↓ bet events
┌─────────────────────────────────────────────────────┐
│ AGENT LAYER (Partially built)                      │
│                                                      │
│ ✅ Monitor Agent (DONE)                             │
│    - Deterministic rules → LLM for ambiguous cases  │
│    - LangGraph: rule_check → [llm_call] → END      │
│    - Flags risky players                            │
│                                                      │
│ ⏳ Predictor Agent (NEXT)                           │
│    - Takes flagged players                          │
│    - Queries Pinecone for similar patterns          │
│    - Returns churn risk score (0-1)                 │
│                                                      │
│ ⏳ Designer Agent                                    │
│    - High risk players → designs intervention       │
│    - Considers: LTV, preferences, budget            │
│                                                      │
│ ⏳ Validator Agent                                   │
│    - Compliance checks (limits, responsible gaming) │
│                                                      │
│ ⏳ Executor Agent                                    │
│    - Delivers intervention to player                │
│                                                      │
│ ⏳ Analyzer Agent                                    │
│    - Runs 24h later, measures ROI                   │
│    - Feeds learnings back to Pinecone              │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ DATA LAYER (To be integrated)                      │
│                                                      │
│ PostgreSQL:                                         │
│ - Player profiles (ID, type, LTV)                  │
│ - Session history (every bet, timestamp)           │
│ - Intervention history                              │
│ - Compliance records                                │
│                                                      │
│ Redis:                                              │
│ - Active session state (current bankroll, streaks) │
│ - In-flight agent processing                        │
│ - WebSocket connection state                        │
│ - Cache for LLM responses (optional)               │
│                                                      │
│ Pinecone (Vector DB):                               │
│ - Embeddings of player behaviors → outcomes        │
│ - Predictor queries: "similar to current player"   │
│ - Analyzer updates: "this intervention worked"     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ API LAYER (Not built yet)                          │
│ - FastAPI endpoints                                 │
│ - WebSocket for real-time updates                  │
└─────────────────────────────────────────────────────┘
```

## Data Flow

### Current State:
```
Simulator → Monitor → (stops here)
```

### Target Flow:
```
Simulator → Monitor → Predictor → Designer → Validator → Executor
                                                            ↓
                    Analyzer (24h later) ←──────────────────┘
                         ↓
                    Pinecone (learning)
```

## Current Implementation Status

**✅ Completed:**
- Simulation layer generates realistic player behavior
- Monitor agent detects anomalies (hybrid rules + LLM)
- Async LLM calls with OpenAI structured output
- Player context serialization for agents
- LangGraph orchestration for Monitor

**⏳ In Progress:**
- Predictor agent with Pinecone integration

**📋 Todo:**
- Designer agent
- Validator agent
- Executor agent
- Analyzer agent
- PostgreSQL integration
- Redis integration
- FastAPI backend
- WebSocket real-time updates
- Frontend dashboard

## Directory Structure

```
backend/
├── agents/              # AI agents
│   ├── monitor_agent.py      # ✅ Anomaly detection
│   └── pydantic_models/      # Response schemas
├── simulation/          # Player behavior simulation
│   ├── player_types.py       # Whale, grinder, casual
│   ├── behavior_models.py    # Emotional states, churn logic
│   ├── event_generator.py    # Bet generation
│   └── player_simulator.py   # Main orchestrator
├── services/            # External integrations
│   ├── llm_service.py        # OpenAI async client
│   └── player_context_serializer.py  # Format data for agents
├── prompts/             # LLM prompts
│   └── monitor_llm.txt       # Monitor decision prompt
├── models/              # Database models (empty)
├── api/                 # FastAPI routes (empty)
└── db/                  # Database connections (empty)
```

## Next Steps

1. **Build Predictor Agent** - Calculate churn risk using vector similarity
2. **Integrate Pinecone** - Store/query player behavior embeddings
3. **Build Designer Agent** - Create personalized interventions
4. **Add PostgreSQL** - Persist player data and history
5. **Add Redis** - Real-time state management
6. **Build API Layer** - Expose agents via FastAPI
7. **Build Frontend** - Real-time dashboard showing agent decisions
