# Casino Churn Detection System

Real-time AI agents that predict and prevent player churn in online casinos before it happens.

## Why I've built this?**
I've built this simulator to better understand how gambling systems operate and to explore how integrating agents and AI into such systems can influence their behavior and outcomes.

## The Problem

Online gambling is a $60B+ industry, but it has a churn problem. Most players quit within their first few sessions, especially after losing streaks. By the time a casino realizes a player has churned, it's too late.

Traditional approaches react after players leave. They send generic "come back" emails days later, which rarely work. The player is already gone, their trust is broken.

**The insight**: Churn doesn't happen when a player closes their browser. It happens in real-time, during a session, after a sequence of bad bets. You can see it in their behavior - they start betting erratically, doubling down on losses (tilting), or suddenly disengaging. That is the moment to intervene, not days later.

## What This System Does

This platform uses AI agents to watch every bet in real-time and intervene the moment a player shows signs of churning. 

**Three AI agents work together:**

1. **Monitor Agent** - Watches the bet stream, flags concerning behavior
2. **Predictor Agent** - Calculates churn risk by finding similar past players
3. **Designer Agent** - Creates personalized retention offers (cashback, free spins, messages)

The system learns from every intervention. When a high-risk player receives an offer and stays, that success gets stored. When they churn anyway, that failure gets stored too. The agents get smarter over time.

## How It Works Behind the Scenes

### The Simulation Layer

Since I don't have access to real casino data, the system includes a realistic player simulator. It creates 50+ players with distinct behavioral profiles:

- **Whales** (10%): High rollers with €10K bankrolls, bet €200/hand, longer sessions
- **Grinders** (30%): Consistent players, €500 bankroll, bet €10/hand, play daily
- **Casuals** (60%): Entertainment gamblers, €100 bankroll, bet €2/hand, play occasionally

Each player has emotional states that affect their behavior:
- **Neutral**: Normal betting patterns
- **Winning**: Slightly increased bets (confidence)
- **Tilting**: Aggressive betting after losses (danger zone)
- **Bored**: Decreased engagement (warning sign)
- **Recovering**: Post-intervention stabilization

Players place bets every 0.2-0.6 seconds (0.1-0.3 when tilting), with realistic outcomes (5% house edge). Sessions last 20-60 bets, then players take breaks and return later - or they churn. => These numbers are like that for a demo, so that entire session doesn't take too long.

### The AI Agent Pipeline

**1. Monitor Agent (Rule-Based + LLM Hybrid)**

Watches every bet event and applies deterministic rules first:
```
- Consecutive losses >= 5: FLAG
- Tilting state + loss streak: FLAG
- Betting 3x+ typical amount while tilting: FLAG
```

For ambiguous cases (emotional state unclear, unusual patterns), it calls GPT-4o-mini with player context:
```
"Player 23 (Grinder) has lost 4 straight bets, is down €30 (6% of bankroll),
but emotional state is neutral and bet sizes are normal. Flag for intervention?"
```

The LLM returns structured JSON: `{"flag": true/false, "reason": "..."}`

This approach is quite fast, and uses deterministic, rule based approach first and then falls back to the agent if neccessary.

**2. Predictor Agent (Vector Similarity Search)**

When a player is flagged, the Predictor needs to answer: "How likely are they to churn?"

It does this by finding similar players in the past:

1. **Creates an embedding** of the current player's behavior:
   - Recent bet patterns (amounts, wins/losses, emotional state)
   - Session context (bankroll, consecutive streaks, bet history)
   - Player profile (type, LTV, past interventions)

2. **Queries Pinecone** (vector database) for the 10 most similar historical players

3. **Calculates risk score**: If 9/10 similar players churned, risk = 0.90

The magic is in the embeddings. Two players who bet differently but have similar emotional arcs and session trajectories will be "close" in vector space. The Predictor learns patterns that aren't obvious from rules.

**3. Designer Agent (Contextual Intervention Creation)**

High-risk players (>0.7 churn probability) need interventions. The Designer uses GPT-4o-mini to create personalized offers.

It considers:
- **Player type**: Whales prefer bonus cash, Casuals prefer free spins
- **Emotional state**: Tilting players need to calm down (cashback), bored players need excitement (free spins)
- **Financial context**: Must be profitable (LTV > offer cost)
- **Intervention history**: Don't repeat the same offer twice in a row
- **Budget constraints**: Daily limits on total offers sent
- **Success rates**: Query past intervention outcomes to pick the best type

Example Designer reasoning:
```
Player 42 (Casual, €100 bankroll) is tilting after losing €15 in 3 minutes.
Risk score: 0.85 (very high)
LTV: €150, so we can afford ~€15-20 offer

Past data shows:
- Cashback for tilting Casuals: 60% success rate
- Free spins for tilting Casuals: 45% success rate

Offer: 20% cashback (€3) with message:
"We know things got tough. Here's €3 back - take a breath, no rush."
```

The agent outputs structured JSON with intervention details and reasoning.

### The Learning Loop

Every intervention creates a "snapshot" stored in Pinecone:
- Player state at intervention time (embeddings)
- Intervention type and amount
- **Outcome** (initially "pending")

24 hours later, the Evaluator checks: Did the player return and keep playing, or did they churn?

The outcome gets written back to Pinecone. Now when the Predictor searches for similar players, it sees not just behavior patterns, but which interventions worked.

This creates a feedback loop:
```
Monitor flags player → Predictor calculates risk → Designer creates offer
                                ↓
                        Player responds (or doesn't)
                                ↓
                    Outcome stored in Pinecone
                                ↓
                Future predictions get smarter
```
## Technology Stack

**Frontend**
- React + TypeScript for the dashboard
- Vite
- WebSockets for real-time simulated bet stream
- CSS Grid for responsive layout

**Backend**
- FastAPI for API and WebSocket server
- Asyncio for concurrent player simulation and agent processing
- LangGraph for agent orchestration
- LangChain for LLM integrations

**AI & ML**
- OpenAI GPT-4o-mini
- OpenAI text-embedding-3-small for creating behavior embeddings
- Pinecone vector database for similarity search

**Data Storage**
- PostgreSQL
- Pinecone 

**Deployment**
- Docker + Docker Compose for containerization
- Google Cloud Platform (GCP) Compute Engine for hosting
- Nginx as reverse proxy (frontend serving + WebSocket handling)

## Project Structure

```
casino_churn_detection/
├── backend/
│   ├── agents/              # AI agents (Monitor, Predictor, Designer)
│   │   ├── monitor_agent.py
│   │   ├── predictor_agent.py
│   │   └── designer_agent.py
│   ├── simulation/          # Player behavior simulation
│   │   ├── player_types.py       # Whale, Grinder, Casual profiles
│   │   ├── behavior_models.py    # Emotional states, churn logic
│   │   ├── event_generator.py    # Bet generation with house edge
│   │   └── player_simulator.py   # Main simulation orchestrator
│   ├── orchestration/       # Agent coordination
│   │   └── agent_coordinator.py  # Routes players through agent pipeline
│   ├── services/
│   │   ├── domain/          # Business logic
│   │   │   ├── knowledge_service.py      # Pinecone operations
│   │   │   ├── player_context_serializer.py  # Format data for agents
│   │   │   └── intervention_evaluator.py  # Track intervention success
│   │   └── external/        # External API clients
│   │       ├── embedding_service.py   # OpenAI embeddings
│   │       └── pinecone_service.py    # Vector DB client
│   ├── api/
│   │   └── main.py          # FastAPI app + WebSocket endpoint
│   └── prompts/             # LLM prompts
│       ├── monitor_llm.txt
│       ├── predictor_prompt.txt
│       └── designer_prompt.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   │   ├── PlayerCard.tsx     # Individual player display
│   │   │   ├── PlayerGrid.tsx     # Grid of all players
│   │   │   ├── Stats.tsx          # System stats panel
│   │   │   └── PlayerDetailModal.tsx  # Detailed player view
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts    # WebSocket connection management
│   │   ├── utils/
│   │   │   └── player.ts          # Player data utilities
│   │   ├── App.tsx          # Main app component
│   │   └── styles.css       # Global styles
│   └── package.json
├── database/
│   └── db_schema.sql        # PostgreSQL schema
├── docker-compose.yml       # Docker orchestration
├── .env                     # Environment variables (create this)
└── requirements.txt         # Python dependencies
```

## Key Features

- **Real-time monitoring**: Every bet analyzed as it happens
- **Behavioral simulation**: Realistic player types with emotional states
- **AI agent collaboration**: Monitor → Predictor → Designer pipeline
- **Vector similarity search**: Find patterns in historical player behavior
- **Contextual interventions**: Personalized offers based on player profile and state
- **Learning from outcomes**: System improves as more data accumulates
- **Live dashboard**: WebSocket-powered UI showing all player activity
- **Visual feedback**: Cards flash when status changes (flagged, intervention, churn)
- **Asynchronous processing**: Agents run in background, don't block bet generation

## How to Use the Dashboard

Once running, you'll see:

1. **Stats Panel** (top)
   - Active Players: Currently in a session
   - High Risk Players: Flagged by Monitor or have interventions
   - AI Interventions Sent: Active retention offers

2. **Player Grid** (main area)
   - Each card shows: Player ID, Status Badge, Churn Risk Score, Last Activity
   - Cards flash when updated (new bet, flagged, intervention)
   - Color-coded borders: Green (active), Blue (flagged), Orange (intervention), Red (churned)

3. **Click any player card** to see detailed modal with:
   - Full player stats (risk score, status, total wagers, win rate)
   - Monitoring status (flagged, churned, bets tracked)
   - AI intervention details (type, amount, message, reasoning)
   - Betting history (last 10 bets)
   - Activity log (if available)

## Development

### Running Tests

```bash
# Backend tests
pytest backend/tests/

# Frontend tests
cd frontend
npm test
```

### Modifying Agent Behavior

Edit prompts in `backend/prompts/`:
- `monitor_llm.txt` - Monitor decision logic
- `predictor_prompt.txt` - Risk calculation reasoning
- `designer_prompt.txt` - Intervention creation logic

Agents will use updated prompts on next run (no code changes needed).

### Adjusting Simulation Speed

In `backend/api/main.py`, line 87:
```python
await simulator_instance.run_simulation(tick_interval_seconds=0.5)
```

Change `0.5` to adjust tick speed (lower = faster, higher = slower).

### Adding New Player Types

Edit `backend/simulation/player_types.py` to define new profiles with different:
- Bet sizing patterns
- Emotional state thresholds
- Churn probabilities
- Intervention preferences

Questions? Open an issue or reach out.