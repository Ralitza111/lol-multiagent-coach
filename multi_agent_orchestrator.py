"""
Multi-Agent Orchestrator for LoL Coach
Coordinates multiple specialized agents to handle complex queries.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from specialized_agents import BaseLoLAgent

# Setup logging
logger = logging.getLogger(__name__)


@dataclass
class AgentTask:
    """Represents a task assigned to a specific agent."""
    agent_name: str
    task_description: str
    priority: int = 1  # 1=highest, higher numbers = lower priority
    dependencies: List[str] = None  # Tasks that must complete first
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class AgentResponse:
    """Response from an agent."""
    agent_name: str
    task_description: str
    response: str
    success: bool = True
    error: Optional[str] = None


class MultiAgentOrchestrator:
    """
    Orchestrates multiple specialized agents to handle complex queries
    that require expertise from multiple domains.
    """
    
    def __init__(
        self,
        llm: ChatOpenAI,
        agents: Dict[str, BaseLoLAgent],
        max_agent_calls: int = 5
    ):
        self.llm = llm
        self.agents = agents
        self.max_agent_calls = max_agent_calls
        
        self.planning_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an orchestrator for a multi-agent League of Legends coaching system.

Available Agents:
- match_analyzer: Analyzes match history and performance
- build_advisor: Recommends builds, runes, and champions
- video_guide: Finds YouTube tutorials and guides
- knowledge_base: Explains game concepts and terminology

Your job is to break down complex user queries into specific tasks for each agent.

Guidelines:
1. Identify which agents are needed
2. Create specific, focused tasks for each agent
3. Consider task dependencies (some tasks need others to complete first)
4. Keep tasks simple and focused
5. Aim for 2-4 agent calls maximum

For example, "I'm losing as Jinx, help me improve" might need:
1. match_analyzer: "Analyze recent Jinx matches and identify performance issues"
2. build_advisor: "Recommend optimal Jinx builds and runes"
3. video_guide: "Find Jinx improvement guides and tutorials"

Return a JSON array of tasks with: agent_name, task_description, priority (1-5, 1=highest)"""),
            ("human", "{query}")
        ])
    
    def plan_tasks(self, query: str) -> List[AgentTask]:
        """
        Plan which agents to call and what tasks to assign them.
        
        Args:
            query: Complex user query requiring multiple agents
            
        Returns:
            List of AgentTask objects
        """
        logger.info(f"Orchestrator planning for query: {query[:100]}...")
        print(f"\n🎭 Orchestrator Planning:")
        print(f"   Query: {query}")
        
        try:
            # Use LLM to plan tasks
            chain = self.planning_prompt | self.llm
            response = chain.invoke({"query": query})
            
            # For now, simple heuristic-based planning
            # (In production, parse LLM JSON response)
            tasks = self._heuristic_planning(query)
            
            logger.info(f"Planned {len(tasks)} tasks for orchestration")
            print(f"   📋 Planned {len(tasks)} tasks:")
            for i, task in enumerate(tasks, 1):
                print(f"      {i}. [{task.agent_name}] {task.task_description[:60]}...")
            
            return tasks
            
        except Exception as e:
            logger.error(f"Planning failed: {str(e)}", exc_info=True)
            # Fallback: create a single task for match analyzer
            return [AgentTask(
                agent_name="match_analyzer",
                task_description=query,
                priority=1
            )]
    
    def _heuristic_planning(self, query: str) -> List[AgentTask]:
        """
        Simple heuristic-based task planning.
        Replace with LLM-based planning in production.
        """
        query_lower = query.lower()
        tasks = []
        
        # Check for pregame/draft strategy needs (check this first as it's pre-game specific)
        if any(word in query_lower for word in [
            "ban", "pick", "select", "draft", "champion select", "team comp",
            "counter pick", "who should i", "what champion", "composition"
        ]):
            tasks.append(AgentTask(
                agent_name="pregame_agent",
                task_description=f"Provide champion select and draft strategy for: {query}",
                priority=1
            ))
        
        # Check for match analysis needs
        if any(word in query_lower for word in [
            "match", "game", "losing", "winning", "performance", "recent", "history"
        ]):
            tasks.append(AgentTask(
                agent_name="match_analyzer",
                task_description=f"Analyze recent match performance related to: {query}",
                priority=1
            ))
        
        # Check for build advice needs
        if any(word in query_lower for word in [
            "build", "items", "rune", "champion", "counter", "what should i"
        ]) and "ban" not in query_lower and "pick" not in query_lower:
            tasks.append(AgentTask(
                agent_name="build_advisor",
                task_description=f"Provide build and champion recommendations for: {query}",
                priority=2
            ))
        
        # Check for video guide needs
        if any(word in query_lower for word in [
            "video", "guide", "tutorial", "learn", "how to", "show me", "watch"
        ]):
            tasks.append(AgentTask(
                agent_name="video_guide",
                task_description=f"Find relevant video guides for: {query}",
                priority=3
            ))
        
        # Check for knowledge/explanation needs
        if any(word in query_lower for word in [
            "what is", "explain", "mean", "how does", "why", "concept"
        ]):
            tasks.append(AgentTask(
                agent_name="knowledge_base",
                task_description=f"Explain concepts related to: {query}",
                priority=2
            ))
        
        # If no specific tasks identified, use all agents
        if not tasks:
            tasks = [
                AgentTask("match_analyzer", f"Analyze relevant matches for: {query}", 1),
                AgentTask("build_advisor", f"Provide recommendations for: {query}", 2),
                AgentTask("video_guide", f"Find helpful guides for: {query}", 3)
            ]
        
        # Sort by priority
        tasks.sort(key=lambda t: t.priority)
        
        # Limit to max_agent_calls
        return tasks[:self.max_agent_calls]
    
    def execute_tasks(
        self,
        tasks: List[AgentTask],
        thread_id: str = "orchestrator"
    ) -> List[AgentResponse]:
        """
        Execute all planned tasks using the appropriate agents.
        
        Args:
            tasks: List of tasks to execute
            thread_id: Thread ID for agent memory
            
        Returns:
            List of AgentResponse objects
        """
        responses = []
        
        print(f"\n🔄 Executing Tasks:")
        
        for i, task in enumerate(tasks, 1):
            agent = self.agents.get(task.agent_name)
            
            if not agent:
                print(f"   ❌ Agent '{task.agent_name}' not found, skipping")
                responses.append(AgentResponse(
                    agent_name=task.agent_name,
                    task_description=task.task_description,
                    response="",
                    success=False,
                    error=f"Agent not found: {task.agent_name}"
                ))
                continue
            
            try:
                print(f"   {i}/{len(tasks)} Calling {task.agent_name}...")
                logger.info(f"Executing task {i}/{len(tasks)} on {task.agent_name}")
                response_text = agent.invoke(task.task_description, thread_id)
                
                responses.append(AgentResponse(
                    agent_name=task.agent_name,
                    task_description=task.task_description,
                    response=response_text,
                    success=True
                ))
                logger.info(f"{task.agent_name} completed successfully")
                print(f"   ✅ {task.agent_name} completed")
                
            except Exception as e:
                logger.error(f"{task.agent_name} failed: {str(e)}", exc_info=True)
                print(f"   ❌ {task.agent_name} failed: {str(e)}")
                responses.append(AgentResponse(
                    agent_name=task.agent_name,
                    task_description=task.task_description,
                    response="",
                    success=False,
                    error=str(e)
                ))
        
        return responses
    
    def synthesize_responses(
        self,
        query: str,
        responses: List[AgentResponse]
    ) -> str:
        """
        Synthesize multiple agent responses into a coherent answer.
        
        Args:
            query: Original user query
            responses: List of agent responses
            
        Returns:
            Synthesized final response
        """
        print(f"\n🔮 Synthesizing {len(responses)} responses...")
        
        # Build context from all successful responses
        context_parts = []
        for resp in responses:
            if resp.success:
                agent_icon = {
                    "match_analyzer": "🎯",
                    "build_advisor": "🛠️",
                    "video_guide": "🎬",
                    "knowledge_base": "📚"
                }.get(resp.agent_name, "🤖")
                
                context_parts.append(
                    f"{agent_icon} **{resp.agent_name.replace('_', ' ').title()}:**\n{resp.response}"
                )
        
        if not context_parts:
            return "❌ I wasn't able to get information from any agents. Please try rephrasing your question."
        
        # Use LLM to synthesize
        synthesis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are synthesizing responses from multiple specialized agents into one coherent answer.

Your job:
1. Combine information from all agents
2. Remove redundancy
3. Create a natural, flowing response
4. Maintain all important details
5. Structure the response logically

Keep the emoji icons for each section to show which agent contributed what."""),
            ("human", """Original Query: {query}

Agent Responses:
{responses}

Synthesize these responses into one comprehensive, well-structured answer.""")
        ])
        
        chain = synthesis_prompt | self.llm
        result = chain.invoke({
            "query": query,
            "responses": "\n\n".join(context_parts)
        })
        
        return result.content
    
    def handle_query(self, query: str, thread_id: str = "orchestrator") -> str:
        """
        Handle a complex query by orchestrating multiple agents.
        
        Args:
            query: User query requiring multiple agents
            thread_id: Thread ID for agent memory
            
        Returns:
            Synthesized response from all agents
        """
        # Plan tasks
        tasks = self.plan_tasks(query)
        
        # Execute tasks
        responses = self.execute_tasks(tasks, thread_id)
        
        # Synthesize responses
        final_response = self.synthesize_responses(query, responses)
        
        return final_response


def create_orchestrator(
    llm: ChatOpenAI,
    agents: Dict[str, BaseLoLAgent]
) -> MultiAgentOrchestrator:
    """
    Create a configured multi-agent orchestrator.
    
    Args:
        llm: ChatOpenAI instance
        agents: Dictionary of specialized agents
        
    Returns:
        Configured MultiAgentOrchestrator
    """
    return MultiAgentOrchestrator(llm, agents)
