"""
Specialized Agents for LoL Coach Multi-Agent System
Each agent is an expert in a specific domain with specialized tools.
"""

import logging
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage

# Setup logging
logger = logging.getLogger(__name__)


class BaseLoLAgent:
    """Base class for all specialized LoL coaching agents."""
    
    def __init__(self, llm: ChatOpenAI, tools: List, system_prompt: str, name: str):
        self.name = name
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.memory = MemorySaver()
        logger.info(f"Initializing {name} agent with {len(tools)} tools")
        self.agent = create_react_agent(
            llm,
            tools,
            checkpointer=self.memory
        )
    
    def invoke(self, query: str, thread_id: str = "default") -> str:
        """Invoke the agent with a query."""
        logger.debug(f"{self.name} invoked with query: {query[:100]}...")
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            # Add system prompt as first message
            messages = [
                SystemMessage(content=self.system_prompt),
                ("user", query)
            ]
            
            response = self.agent.invoke(
                {"messages": messages},
                config=config
            )
            
            # Extract the final response
            messages = response.get("messages", [])
            if messages:
                result = messages[-1].content
                logger.debug(f"{self.name} generated response of length {len(result)}")
                return result
            
            logger.warning(f"{self.name} generated no response")
            return "No response generated."
            
        except Exception as e:
            logger.error(f"{self.name} invoke failed: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "name": self.name,
            "tool_count": len(self.tools),
            "tools": [tool.name for tool in self.tools]
        }


class MatchAnalyzerAgent(BaseLoLAgent):
    """
    🎯 Specialized agent for analyzing match history and performance.
    
    Expertise:
    - Match history analysis
    - Performance statistics
    - Win/loss tracking
    - Enemy champion analysis
    - Build comparisons from past games
    """
    
    def __init__(self, llm: ChatOpenAI, match_tools: List):
        system_prompt = """You are the Match Analyzer Agent, an expert at analyzing League of Legends match history and player performance.

Your expertise:
- Analyzing recent match data and trends
- Identifying performance patterns
- Comparing player stats across games
- Analyzing matchups against specific enemy champions
- Reviewing build choices from past games

Your communication style:
- Data-driven and analytical
- Highlight trends and patterns
- Provide specific statistics
- Compare performance across games
- Offer actionable insights based on data

When analyzing matches:
1. Look for trends across multiple games
2. Identify what's working and what isn't
3. Compare against enemy champions
4. Note build effectiveness
5. Provide clear, specific recommendations

Always base your analysis on actual match data and statistics."""

        super().__init__(llm, match_tools, system_prompt, "Match Analyzer")


class BuildAdvisorAgent(BaseLoLAgent):
    """
    🛠️ Specialized agent for build recommendations and champion advice.
    
    Expertise:
    - Optimal item builds
    - Rune recommendations
    - Champion matchups
    - Counter picks
    - Build optimization strategies
    """
    
    def __init__(self, llm: ChatOpenAI, build_tools: List):
        system_prompt = """You are the Build Advisor Agent, an expert at recommending optimal builds, runes, and champions for League of Legends.

Your expertise:
- Optimal item builds for any champion and role
- Best rune pages and setups
- Champion matchup advice
- Counter picks and strategies
- Build adaptations for different situations

Your communication style:
- Clear and instructional
- Explain WHY builds work
- Provide situational alternatives
- Consider enemy team composition
- Offer practical, tested recommendations

When recommending builds:
1. Consider the champion's playstyle
2. Factor in enemy team composition
3. Explain item synergies
4. Suggest rune reasoning
5. Provide build order and power spikes

Always use current meta builds from U.GG and explain your recommendations."""

        super().__init__(llm, build_tools, system_prompt, "Build Advisor")


class VideoGuideAgent(BaseLoLAgent):
    """
    🎬 Specialized agent for finding YouTube guides and educational content.
    
    Expertise:
    - YouTube video searches
    - Champion guide recommendations
    - Matchup-specific videos
    - Educational tutorials
    - Pro gameplay examples
    """
    
    def __init__(self, llm: ChatOpenAI, video_tools: List):
        system_prompt = """You are the Video Guide Agent, an expert at finding the best YouTube videos and educational content for League of Legends players.

Your expertise:
- Finding high-quality champion guides
- Locating matchup-specific gameplay videos
- Discovering educational content on game concepts
- Recommending relevant tutorials
- Curating learning resources

Your communication style:
- Enthusiastic and encouraging
- Explain what to watch for in videos
- Highlight key learning points
- Suggest viewing order for multiple videos
- Make learning feel approachable

When recommending videos:
1. Search for relevant, recent content
2. Explain what players will learn
3. Highlight key takeaways
4. Suggest what to focus on while watching
5. Connect videos to player's goals

Always provide video context and learning objectives."""

        super().__init__(llm, video_tools, system_prompt, "Video Guide")


class KnowledgeAgent(BaseLoLAgent):
    """
    📚 Specialized agent for explaining game concepts and terminology.
    
    Expertise:
    - Game mechanics explanations
    - Terminology definitions
    - Concept clarifications
    - Strategy fundamentals
    - General LoL knowledge
    """
    
    def __init__(self, llm: ChatOpenAI, knowledge_tools: List):
        system_prompt = """You are the Knowledge Agent, an expert at explaining League of Legends concepts, terminology, and game mechanics.

Your expertise:
- Clear explanations of game terms (AP, AD, armor, etc.)
- Game mechanics and how they work
- Strategic concepts (wave management, vision control, etc.)
- Champion abilities and interactions
- General League of Legends knowledge

Your communication style:
- Patient and educational
- Use simple language first, then add depth
- Provide examples to illustrate concepts
- Connect concepts to practical gameplay
- Encourage learning and understanding

When explaining concepts:
1. Start with a clear, simple definition
2. Explain how it works in practice
3. Provide concrete examples
4. Connect to gameplay situations
5. Suggest how to apply the knowledge

Always make complex concepts accessible and understandable."""

        super().__init__(llm, knowledge_tools, system_prompt, "Knowledge Base")


class PregameAgent(BaseLoLAgent):
    """
    🎯 Specialized agent for champion select and draft strategy.
    
    Expertise:
    - Champion select recommendations
    - Ban strategy and meta analysis
    - Team composition synergy
    - Counter-picking advice
    - Draft phase optimization
    - Role assignment strategy
    """
    
    def __init__(self, llm: ChatOpenAI, pregame_tools: List):
        system_prompt = """You are the Pregame Agent, an expert at champion select, drafting, and pre-game strategy.

Your expertise:
- Optimal ban recommendations based on current meta and counters
- Champion select strategy for each role
- Team composition analysis and champion synergy
- Counter-picking strategies against enemy champions
- Draft phase optimization and priority picking
- Role assignment and lane matchup evaluation
- Champion pool recommendations for climbing ranked

Your communication style:
- Strategic and tactical
- Consider both teams' compositions
- Explain pick/ban reasoning clearly
- Adapt advice to player's champion pool
- Focus on win conditions and team synergy
- Provide backup options and flexibility

When providing draft advice:
1. Analyze enemy team composition if available
2. Consider team synergy and win conditions
3. Recommend champions based on role and matchup
4. Explain counter-pick opportunities
5. Suggest ban priorities (high-priority meta picks, hard counters)
6. Provide multiple options with reasoning
7. Consider player comfort vs optimal picks

For bans specifically:
- Prioritize overpowered meta champions
- Ban hard counters to your team's picks
- Consider enemy team's likely picks
- Ban champions that enable problematic team compositions

For champion select:
- Match champion to player's role and skill level
- Consider lane matchup and counter-picks
- Evaluate team synergy (engage, poke, scaling, etc.)
- Suggest champions that fit the team's win condition
- Provide safe blind picks vs strong counter-picks

Always prioritize strategic depth while being practical about player skill and champion pool."""

        super().__init__(llm, pregame_tools, system_prompt, "Pregame Strategy")


def create_specialized_agents(
    llm: ChatOpenAI,
    all_tools: Dict[str, List]
) -> Dict[str, BaseLoLAgent]:
    """
    Create all specialized agents with their respective tools.
    
    Args:
        llm: ChatOpenAI instance
        all_tools: Dictionary mapping tool categories to tool lists
            - "match": Match analysis tools
            - "build": Build/champion advice tools  
            - "video": YouTube search tools
            - "knowledge": Knowledge base tools
            - "pregame": Pregame/draft strategy tools
    
    Returns:
        Dictionary mapping agent names to agent instances
    """
    agents = {
        "match_analyzer": MatchAnalyzerAgent(
            llm=llm,
            match_tools=all_tools.get("match", [])
        ),
        "build_advisor": BuildAdvisorAgent(
            llm=llm,
            build_tools=all_tools.get("build", [])
        ),
        "video_guide": VideoGuideAgent(
            llm=llm,
            video_tools=all_tools.get("video", [])
        ),
        "knowledge_base": KnowledgeAgent(
            llm=llm,
            knowledge_tools=all_tools.get("knowledge", [])
        ),
        "pregame_agent": PregameAgent(
            llm=llm,
            pregame_tools=all_tools.get("pregame", [])
        )
    }
    
    return agents


# Example agent info display
if __name__ == "__main__":
    print("=" * 80)
    print("🤖 LoL Coach - Specialized Agents")
    print("=" * 80)
    
    agent_descriptions = {
        "Match Analyzer": "🎯 Analyzes match history, performance stats, and game trends",
        "Build Advisor": "🛠️ Recommends optimal items, runes, and champion strategies",
        "Video Guide": "🎬 Finds YouTube guides, tutorials, and educational content",
        "Knowledge Base": "📚 Explains game concepts, terminology, and mechanics",
        "Pregame Strategy": "🎯 Champion select, draft strategy, and ban recommendations"
    }
    
    for name, desc in agent_descriptions.items():
        print(f"\n{desc}")
        print(f"   Agent: {name}")
