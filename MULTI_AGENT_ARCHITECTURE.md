# Multi-Agent System Architecture

## 🏗️ Overview

The LoL Coach now uses a **multi-agent architecture** with intelligent routing to provide specialized, expert-level coaching across different domains.

---

## 🎯 System Components

### 1. **Query Router** (`multi_agent_router.py`)

The router analyzes user queries and intelligently routes them to the most appropriate agent.

**Features:**
- Intent classification using GPT-4o-mini
- Structured output with Pydantic models
- Multi-agent detection for complex queries
- Detailed logging of routing decisions

**Example Routing:**
```python
"Analyze my matches" → match_analyzer
"What items for Ahri?" → build_advisor
"Find Yasuo guides" → video_guide
"Explain AP" → knowledge_base
"I'm losing as Jinx, help me improve" → orchestrator (multi-agent)
```

---

### 2. **Specialized Agents** (`specialized_agents.py`)

Four expert agents, each focused on a specific coaching domain:

#### 🎯 Match Analyzer Agent
**Expertise:**
- Match history analysis
- Performance statistics
- Win/loss tracking
- Enemy champion analysis
- Build effectiveness from past games

**Tools:**
- `get_summoner_profile`
- `analyze_recent_matches`
- `analyze_enemy_champions`
- `compare_my_build`

**Personality:** Data-driven, analytical, pattern-focused

---

#### 🛠️ Build Advisor Agent
**Expertise:**
- Optimal item builds
- Rune recommendations
- Champion matchups
- Counter picks
- Build adaptations

**Tools:**
- `get_optimal_build`
- `get_champion_matchups`

**Personality:** Instructional, explanatory, practical

---

#### 🎬 Video Guide Agent
**Expertise:**
- YouTube video searches
- Champion guides
- Matchup-specific videos
- Educational tutorials
- Pro gameplay examples

**Tools:**
- `find_champion_guides`
- `find_matchup_videos`
- `find_educational_videos`

**Personality:** Enthusiastic, encouraging, learning-focused

---

#### 📚 Knowledge Agent
**Expertise:**
- Game mechanics explanations
- Terminology definitions
- Concept clarifications
- Strategy fundamentals

**Tools:**
- `search_lol_knowledge`

**Personality:** Patient, educational, simple-to-complex explanations

---

### 3. **Multi-Agent Orchestrator** (`multi_agent_orchestrator.py`)

Coordinates multiple agents for complex queries requiring cross-domain expertise.

**Features:**
- Task planning and decomposition
- Dependency management
- Parallel agent execution
- Response synthesis

**Example Workflow:**
```
Query: "I'm losing as Jinx, what should I do?"

Orchestrator Plans:
1. Match Analyzer: "Analyze recent Jinx performance"
2. Build Advisor: "Recommend optimal Jinx builds"
3. Video Guide: "Find Jinx improvement guides"

→ Synthesizes all responses into coherent answer
```

---

### 4. **Main System** (`multi_agent_coach.py`)

Integrates all components into a unified coaching system.

**Architecture Flow:**
```
User Query
    ↓
Router (classify intent)
    ↓
Single Agent ← OR → Orchestrator → Multiple Agents
    ↓                                     ↓
Response                           Synthesized Response
```

---

## 🚀 Usage

### Basic Usage

```python
from multi_agent_coach import create_multi_agent_coach

# Create the system
coach = create_multi_agent_coach()

# Ask questions - automatically routed
response = coach.chat("Analyze my recent matches")
response = coach.chat("What items for Ahri?")
response = coach.chat("I'm losing as Jinx, help me improve")
```

### With Custom Configuration

```python
coach = create_multi_agent_coach(
    openai_api_key="your-key",
    riot_api_key="your-key",
    region="na1",
    routing_value="americas"
)
```

---

## 📊 Routing Logic

### Single Agent Queries

| Query Type | Routed To | Example |
|------------|-----------|---------|
| Match history | match_analyzer | "Show my recent games" |
| Performance stats | match_analyzer | "How am I doing?" |
| Item builds | build_advisor | "What to build on Ahri?" |
| Runes | build_advisor | "Best runes for Jinx?" |
| Champion advice | build_advisor | "Counters to Yasuo?" |
| Video search | video_guide | "Find Ahri guides" |
| Tutorials | video_guide | "Wave management videos" |
| Definitions | knowledge_base | "What is AP?" |
| Concepts | knowledge_base | "Explain armor" |

### Multi-Agent Queries

Complex queries automatically trigger the orchestrator:

- "I'm losing, help me improve" → match_analyzer + build_advisor + video_guide
- "Why am I dying so much as Zed?" → match_analyzer + knowledge_base + video_guide
- "How to get better at Ahri?" → build_advisor + video_guide + knowledge_base

---

## 🎭 Agent Personalities

Each agent has a distinct communication style optimized for its domain:

### Match Analyzer 🎯
- **Style:** Analytical, data-driven
- **Focus:** Trends, patterns, statistics
- **Example:** "Looking at your last 10 games, your KDA is highest when..."

### Build Advisor 🛠️
- **Style:** Instructional, practical
- **Focus:** Items, strategies, explanations
- **Example:** "For Ahri, build Luden's first because it synergizes with..."

### Video Guide 🎬
- **Style:** Enthusiastic, encouraging
- **Focus:** Learning resources, key takeaways
- **Example:** "Check out this guide! Focus on the combo section around 5:30..."

### Knowledge Agent 📚
- **Style:** Patient, educational
- **Focus:** Clear explanations, examples
- **Example:** "AP (Ability Power) increases your magic damage. For example, if Ahri's Q..."

---

## 🔄 Orchestrator Workflow

For complex queries, the orchestrator:

1. **Plan:** Break query into sub-tasks for each agent
2. **Execute:** Run agents in priority order
3. **Synthesize:** Combine responses into coherent answer

**Example:**
```
Query: "I keep losing as Jinx, what should I do?"

Planning:
  Priority 1: match_analyzer → Analyze recent Jinx performance
  Priority 2: build_advisor → Recommend optimal Jinx builds  
  Priority 3: video_guide → Find Jinx improvement guides

Execution:
  ✅ match_analyzer: "Your average KDA is 3.2/5.1/7.8..."
  ✅ build_advisor: "Build Kraken Slayer first for DPS..."
  ✅ video_guide: "Found 3 high-level Jinx guides..."

Synthesis:
  Combines all responses with sections:
  🎯 Performance Analysis: ...
  🛠️ Build Recommendations: ...
  🎬 Learning Resources: ...
```

---

## 🎨 Benefits of Multi-Agent Architecture

### 1. **Specialized Expertise**
- Each agent is an expert in its domain
- Focused prompts and tools per agent
- Better quality responses

### 2. **Intelligent Routing**
- Automatic detection of query intent
- Right expert for each question
- Seamless user experience

### 3. **Scalability**
- Easy to add new agents
- Independent agent development
- Modular architecture

### 4. **Complex Query Handling**
- Orchestrator coordinates multiple experts
- Breaks down complex problems
- Comprehensive answers

### 5. **Better Context**
- Each agent maintains conversation memory
- Specialized system prompts
- Domain-specific personality

---

## 🛠️ Technical Details

### Router Implementation

Uses **structured output** with Pydantic:
```python
class RouteQuery(BaseModel):
    agent: Literal["match_analyzer", "build_advisor", ...]
    reasoning: str
    needs_multiple_agents: bool
```

### Agent Base Class

All agents inherit from `BaseLoLAgent`:
```python
class BaseLoLAgent:
    - name: Agent identifier
    - llm: Language model
    - tools: Agent-specific tools
    - system_prompt: Domain expertise prompt
    - memory: Conversation state
```

### Orchestrator Tasks

Uses dataclasses for task management:
```python
@dataclass
class AgentTask:
    agent_name: str
    task_description: str
    priority: int
    dependencies: List[str]
```

---

## 📈 Future Enhancements

### Planned Improvements:
1. **LLM-based task planning** (currently heuristic)
2. **Agent-to-agent communication**
3. **Shared memory across agents**
4. **Performance monitoring and analytics**
5. **Custom agent creation API**
6. **Agent fine-tuning for LoL domain**

---

## 🧪 Testing

Test the system with various query types:

```python
# Run the test suite
python multi_agent_coach.py

# Or test individual components
python multi_agent_router.py  # Test routing
python specialized_agents.py  # Test agent creation
```

---

## 📚 File Structure

```
lol-coach-agent/
├── multi_agent_router.py          # Query routing and intent classification
├── specialized_agents.py          # Four specialized agent implementations
├── multi_agent_orchestrator.py   # Multi-agent coordination
├── multi_agent_coach.py           # Main integration and API
├── lol_coach_agent.py            # Original single-agent system (legacy)
└── MULTI_AGENT_ARCHITECTURE.md   # This file
```

---

## 🎯 Summary

The multi-agent architecture provides:

✅ **Specialized Expertise** - Focused agents for each domain  
✅ **Intelligent Routing** - Automatic query classification  
✅ **Complex Handling** - Orchestrator for multi-domain queries  
✅ **Better Responses** - Domain-specific prompts and tools  
✅ **Scalable Design** - Easy to extend with new agents  

**Ready to provide expert-level coaching across all aspects of League of Legends! 🚀**
