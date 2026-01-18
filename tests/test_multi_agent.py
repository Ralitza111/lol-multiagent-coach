"""
Unit Tests for Multi-Agent LoL Coach System
Tests routing logic, agent responses, and error handling.
"""

import pytest
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from multi_agent_coach import create_multi_agent_coach
from multi_agent_router import create_router, RouteQuery


# Load environment variables for tests
load_dotenv()


@pytest.fixture
def coach():
    """Fixture to create a test coach instance"""
    return create_multi_agent_coach()


@pytest.fixture
def router():
    """Fixture to create a test router instance"""
    return create_router(os.getenv("OPENAI_API_KEY"))


class TestRouting:
    """Test the routing logic"""
    
    def test_pregame_agent_routing(self, router):
        """Test that ban-related queries route to pregame_agent"""
        route = router.route("Who should I ban in ranked?")
        assert route.agent == "pregame_agent"
        assert isinstance(route.reasoning, str)
        assert len(route.reasoning) > 0
    
    def test_pregame_agent_pick_routing(self, router):
        """Test that champion pick queries route to pregame_agent"""
        route = router.route("What champion should I pick for mid lane?")
        assert route.agent == "pregame_agent"
    
    def test_match_analyzer_routing(self, router):
        """Test that match analysis queries route to match_analyzer"""
        route = router.route("Analyze my recent matches")
        assert route.agent == "match_analyzer"
    
    def test_build_advisor_routing(self, router):
        """Test that build queries route to build_advisor"""
        route = router.route("What items should I build on Ahri?")
        assert route.agent == "build_advisor"
    
    def test_video_guide_routing(self, router):
        """Test that video queries route to video_guide"""
        route = router.route("Find Yasuo guides")
        assert route.agent == "video_guide"
    
    def test_knowledge_base_routing(self, router):
        """Test that definition queries route to knowledge_base"""
        route = router.route("What does AP mean?")
        assert route.agent == "knowledge_base"
    
    def test_orchestrator_routing(self, router):
        """Test that complex queries may route to orchestrator"""
        route = router.route("I keep losing as Jinx, help me get better")
        # This could route to orchestrator or match_analyzer
        assert route.agent in ["orchestrator", "match_analyzer"]


class TestAgents:
    """Test the agent functionality"""
    
    def test_coach_creation(self, coach):
        """Test that coach is created with all agents"""
        assert coach is not None
        assert len(coach.agents) == 5
        assert "pregame_agent" in coach.agents
        assert "match_analyzer" in coach.agents
        assert "build_advisor" in coach.agents
        assert "video_guide" in coach.agents
        assert "knowledge_base" in coach.agents
    
    def test_agent_info(self, coach):
        """Test that agents provide info"""
        for agent_name, agent in coach.agents.items():
            info = agent.get_info()
            assert "name" in info
            assert "tool_count" in info
            assert "tools" in info
            assert isinstance(info["tools"], list)
    
    def test_system_info(self, coach):
        """Test system information retrieval"""
        sys_info = coach.get_system_info()
        assert "agents" in sys_info
        assert "router" in sys_info
        assert "orchestrator" in sys_info
        assert sys_info["router"] == "Active"
        assert sys_info["orchestrator"] == "Active"


class TestErrorHandling:
    """Test error handling and fallback logic"""
    
    def test_error_handler(self, coach):
        """Test that error handler returns appropriate messages"""
        # Test API error
        error = Exception("API connection failed")
        response = coach._handle_error(error, "test query")
        assert "API" in response or "api" in response.lower()
        assert len(response) > 0
    
    def test_fallback_response(self, coach):
        """Test fallback response for out-of-scope queries"""
        response = coach._fallback_response("something completely unrelated")
        assert len(response) > 0
        assert "specialize" in response.lower() or "help" in response.lower()
    
    def test_chat_with_invalid_thread(self, coach):
        """Test chat with various thread IDs"""
        # This should not crash even with weird thread IDs
        response = coach.chat("What does AP mean?", thread_id="test_thread_123")
        assert isinstance(response, str)
        assert len(response) > 0


class TestRouteQueryModel:
    """Test the RouteQuery Pydantic model"""
    
    def test_route_query_creation(self):
        """Test creating a RouteQuery instance"""
        route = RouteQuery(
            agent="pregame_agent",
            reasoning="Test reasoning",
            needs_multiple_agents=False
        )
        assert route.agent == "pregame_agent"
        assert route.reasoning == "Test reasoning"
        assert route.needs_multiple_agents is False
    
    def test_route_query_validation(self):
        """Test that invalid agent names are caught"""
        with pytest.raises(Exception):  # Pydantic validation error
            RouteQuery(
                agent="invalid_agent_name",
                reasoning="Test",
                needs_multiple_agents=False
            )


class TestIntegration:
    """Integration tests for end-to-end functionality"""
    
    def test_simple_query_flow(self, coach):
        """Test a simple query from start to finish"""
        response = coach.chat("What does AD mean?")
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_pregame_query_flow(self, coach):
        """Test pregame agent query flow"""
        response = coach.chat("Who should I ban?")
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_knowledge_base_retrieval(self, coach):
        """Test that FAISS knowledge base is loaded and accessible"""
        # Check that knowledge retriever exists
        assert hasattr(coach, 'knowledge_retriever')
        
        # Check that knowledge base agent has tools
        knowledge_agent = coach.agents.get('knowledge_base')
        assert knowledge_agent is not None
        
        info = knowledge_agent.get_info()
        assert info['tool_count'] >= 1, "Knowledge base agent should have at least 1 tool"
    
    def test_knowledge_query_flow(self, coach):
        """Test querying the knowledge base through the agent"""
        response = coach.chat("What is attack damage in League of Legends?")
        assert isinstance(response, str)
        assert len(response) > 0
        # Response should contain relevant information
        assert len(response) > 50, "Knowledge base should provide detailed information"


# Run tests with: pytest tests/test_multi_agent.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
