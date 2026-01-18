"""
Multi-Agent Router for LoL Coach
Routes user queries to specialized agents based on intent classification.
"""

import logging
from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Setup logging
logger = logging.getLogger(__name__)


class RouteQuery(BaseModel):
    """Route a user query to the most relevant agent."""
    
    agent: Literal[
        "match_analyzer",
        "build_advisor", 
        "video_guide",
        "knowledge_base",
        "pregame_agent",
        "orchestrator"
    ] = Field(
        description="The agent that should handle this query"
    )
    
    reasoning: str = Field(
        description="Brief explanation of why this agent was chosen"
    )
    
    needs_multiple_agents: bool = Field(
        default=False,
        description="True if query requires multiple agents to collaborate"
    )


class QueryRouter:
    """
    Intelligent router that classifies user queries and directs them
    to the appropriate specialized agent.
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.structured_llm = llm.with_structured_output(RouteQuery)
        
        self.routing_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at routing League of Legends coaching queries to specialized agents.

Available Agents:

1. **match_analyzer** - Handles:
   - Match history analysis
   - Performance statistics
   - Win/loss tracking
   - Recent game reviews
   - Enemy champion analysis
   - Build comparisons from past games
   - Examples: "Analyze my recent matches", "How did I do vs Zed?", "Show my match history"

2. **build_advisor** - Handles:
   - Optimal item builds
   - Rune recommendations
   - Champion matchups
   - Build optimization
   - Counter picks
   - Examples: "What items should I build on Ahri?", "Best runes for Jinx?", "Counters to Yasuo?"

3. **video_guide** - Handles:
   - YouTube video searches
   - Champion guides
   - Matchup videos
   - Educational content
   - Tutorial requests
   - Examples: "Find Ahri guides", "Videos about wave management", "Ahri vs Zed matchup videos"

4. **knowledge_base** - Handles:
   - Game concept explanations
   - Terminology definitions
   - Mechanics explanations
   - General LoL questions
   - Examples: "What is AP?", "Explain armor", "What does split pushing mean?"

5. **pregame_agent** - Handles:
   - Champion select strategy
   - Draft phase advice
   - Ban recommendations
   - Team composition analysis
   - Role and lane assignment
   - Counter-picking in draft
   - Examples: "Who should I ban?", "What champion should I pick?", "Help me with champion select", "Good team comp?"

6. **orchestrator** - Handles:
   - Complex queries needing multiple agents
   - Questions combining match analysis + builds
   - Comprehensive coaching requests
   - Multi-step inquiries
   - Examples: "Analyze my matches and suggest better builds", "Why am I losing and what should I do?"

Routing Guidelines:
- Choose the MOST SPECIFIC agent possible
- Only use orchestrator if query clearly needs 2+ agents
- Match keywords to agent expertise
- Consider user intent, not just keywords
- Default to orchestrator if very unclear

Analyze the query and route it to the best agent."""),
            ("human", "{query}")
        ])
    
    def route(self, query: str) -> RouteQuery:
        """
        Route a user query to the appropriate agent.
        
        Args:
            query: User's question or request
            
        Returns:
            RouteQuery with agent selection and reasoning
        """
        logger.info(f"Routing query: {query[:100]}...")
        
        try:
            chain = self.routing_prompt | self.structured_llm
            result = chain.invoke({"query": query})
            
            # Log routing decision
            logger.info(f"Routed to: {result.agent} - Reason: {result.reasoning}")
            logger.debug(f"Multiple agents needed: {result.needs_multiple_agents}")
            
            print(f"\n🧭 Router Decision:")
            print(f"   Query: {query[:80]}...")
            print(f"   → Routed to: {result.agent}")
            print(f"   Reasoning: {result.reasoning}")
            if result.needs_multiple_agents:
                print(f"   🔄 Multi-agent workflow required")
            
            return result
            
        except Exception as e:
            logger.error(f"Routing failed: {str(e)}", exc_info=True)
            # Fallback to orchestrator for complex queries
            logger.warning("Falling back to orchestrator")
            return RouteQuery(
                agent="orchestrator",
                reasoning=f"Routing error occurred, defaulting to orchestrator: {str(e)}",
                needs_multiple_agents=True
            )
    
    def get_agent_description(self, agent_name: str) -> str:
        """Get a human-readable description of what an agent does."""
        descriptions = {
            "match_analyzer": "🎯 Match Analyzer - Analyzes your game history and performance",
            "build_advisor": "🛠️ Build Advisor - Recommends optimal items, runes, and champions",
            "video_guide": "🎬 Video Guide - Finds YouTube tutorials and gameplay videos",
            "knowledge_base": "📚 Knowledge Base - Explains game concepts and terminology",
            "pregame_agent": "🎯 Pregame Agent - Champion select, drafting, and ban strategy",
            "orchestrator": "🎭 Orchestrator - Coordinates multiple agents for complex requests"
        }
        return descriptions.get(agent_name, agent_name)


def create_router(openai_api_key: str, temperature: float = 0.3) -> QueryRouter:
    """
    Create a configured query router.
    
    Args:
        openai_api_key: OpenAI API key
        temperature: LLM temperature (lower = more deterministic routing)
        
    Returns:
        Configured QueryRouter instance
    """
    llm = ChatOpenAI(
        api_key=openai_api_key,
        model="gpt-4o-mini",
        temperature=temperature
    )
    
    return QueryRouter(llm)


# Example usage and testing
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    router = create_router(os.getenv("OPENAI_API_KEY"))
    
    # Test queries
    test_queries = [
        "Analyze my recent matches",
        "What items should I build on Ahri?",
        "Find some Yasuo guides",
        "What does AP mean?",
        "I keep losing as Jinx, what builds should I use and show me some guides",
        "How did I do against Zed in my last game?",
        "Best runes for Master Yi jungle?",
        "Explain wave management",
        "Find matchup videos for Ahri vs Syndra"
    ]
    
    print("=" * 80)
    print("🧪 Testing Query Router")
    print("=" * 80)
    
    for query in test_queries:
        result = router.route(query)
        print()
