"""
Multi-Agent LoL Coach System
Main integration file connecting router, agents, and orchestrator.
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.tools import tool
from langchain_community.vectorstores import FAISS
from tavily import TavilyClient

# Import API clients and data fetchers
from riot_api import RiotAPI
from data_fetchers import get_optimal_build_ugg, get_champion_stats
from youtube_scraper import YouTubeScraper

# Import multi-agent components
from multi_agent_router import create_router, QueryRouter
from specialized_agents import create_specialized_agents, BaseLoLAgent
from multi_agent_orchestrator import create_orchestrator, MultiAgentOrchestrator

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, f'multi_agent_{datetime.now().strftime("%Y%m%d")}.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_knowledge_base_retriever(openai_api_key: str):
    """
    Load the LoL knowledge base FAISS vector store as a retriever.
    
    Args:
        openai_api_key: OpenAI API key for embeddings
        
    Returns:
        FAISS retriever or None if knowledge base doesn't exist
    """
    embeddings = OpenAIEmbeddings(api_key=openai_api_key)
    
    knowledge_base_path = "./knowledge_base/faiss_index"
    if os.path.exists(knowledge_base_path):
        logger.info(f"Loading FAISS knowledge base from {knowledge_base_path}")
        try:
            vector_store = FAISS.load_local(
                knowledge_base_path,
                embeddings,
                allow_dangerous_deserialization=True
            )
            retriever = vector_store.as_retriever(search_kwargs={"k": 5})
            logger.info("✅ FAISS knowledge base loaded successfully")
            return retriever
        except Exception as e:
            logger.error(f"❌ Error loading FAISS knowledge base: {e}")
            return None
    else:
        logger.warning(f"⚠️  Knowledge base not found at {knowledge_base_path}")
        logger.warning("   Run 'python create_lol_knowledge_base.py' to create it")
        return None


# Import existing tools (from original lol_coach_agent.py)
# These will be distributed among specialized agents


class MultiAgentLoLCoach:
    """
    Multi-agent League of Legends coaching system with intelligent routing.
    """
    
    def __init__(
        self,
        openai_api_key: str,
        riot_api_key: str,
        region: str = "na1",
        routing_value: str = "americas",
        summoner_name: str = None,
        summoner_tag: str = None,
        additional_summoners: list = None
    ):
        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            model="gpt-4o-mini",
            temperature=0.3
        )
        
        # Store API keys and user info for tools
        self.riot_api_key = riot_api_key
        self.region = region
        self.routing_value = routing_value
        self.summoner_name = summoner_name
        self.summoner_tag = summoner_tag
        self.additional_summoners = additional_summoners or []
        
        # Initialize API clients
        self.riot_api = RiotAPI(api_key=riot_api_key, region=region, routing=routing_value)
        self.youtube_scraper = YouTubeScraper()
        
        # Initialize Tavily client for web search
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.tavily_client = TavilyClient(api_key=tavily_api_key) if tavily_api_key else None
        
        # Initialize components
        logger.info("Initializing Multi-Agent LoL Coach System...")
        print("🚀 Initializing Multi-Agent LoL Coach System...")
        
        # Load FAISS knowledge base
        self.knowledge_retriever = load_knowledge_base_retriever(openai_api_key)
        if self.knowledge_retriever:
            print("   ✅ FAISS knowledge base loaded")
        else:
            print("   ⚠️  FAISS knowledge base not available")
        
        # Display tracked summoners
        if summoner_name and summoner_tag:
            primary_summoner = f"{summoner_name}#{summoner_tag}"
            logger.info(f"Primary Summoner: {primary_summoner} ({region.upper()})")
            print(f"   👤 Primary Summoner: {primary_summoner} ({region.upper()})")
            
            if additional_summoners:
                logger.info(f"Additional Summoners: {', '.join(additional_summoners)}")
                print(f"   👥 Additional Summoners: {', '.join(additional_summoners)}")
        
        # 1. Create router
        self.router = create_router(openai_api_key)
        logger.info("Router initialized successfully")
        print("   ✅ Router initialized")
        
        # 2. Organize tools by category
        tools = self._organize_tools()
        
        # 3. Create specialized agents
        self.agents = create_specialized_agents(self.llm, tools)
        logger.info(f"{len(self.agents)} specialized agents created")
        print(f"   ✅ {len(self.agents)} specialized agents created:")
        for name, agent in self.agents.items():
            info = agent.get_info()
            print(f"      • {name}: {info['tool_count']} tools")
        
        # 4. Create orchestrator
        self.orchestrator = create_orchestrator(self.llm, self.agents)
        print("   ✅ Orchestrator initialized")
        
        print("\n✨ Multi-Agent System Ready!\n")
    
    def _organize_tools(self) -> dict:
        """
        Organize all tools into categories for distribution to specialized agents.
        
        Note: This imports tools from the original lol_coach_agent.py
        We'll need to refactor those tools to be importable.
        """
        # Helper function to get tagline for summoner
        def get_tagline_for_summoner(summoner_name: str) -> str:
            """Look up the correct tagline for a summoner name."""
            summoner_name_lower = summoner_name.lower()
            tracked_summoners = [(self.summoner_name, self.summoner_tag)]
            for summoner in self.additional_summoners:
                if "#" in summoner:
                    name, tag = summoner.split("#", 1)
                    tracked_summoners.append((name.strip(), tag.strip()))
            
            for name, tag in tracked_summoners:
                if name.lower() == summoner_name_lower:
                    return tag
            return self.summoner_tag or "NA1"
        
        # === MATCH ANALYSIS TOOLS ===
        match_tools = []
        
        @tool
        def get_summoner_profile(summoner_name: str = None, tag_line: str = None) -> str:
            """
            Get summoner profile information including level, rank, and basic stats.
            If no summoner_name provided, uses the configured default summoner.
            """
            if summoner_name is None:
                summoner_name = self.summoner_name
            if tag_line is None:
                tag_line = get_tagline_for_summoner(summoner_name)
            
            try:
                account_info = self.riot_api.get_account_by_riot_id(summoner_name, tag_line)
                if not account_info:
                    return f"❌ Account '{summoner_name}#{tag_line}' not found."
                
                puuid = account_info.get('puuid')
                summoner_info = self.riot_api.get_summoner_by_puuid(puuid)
                
                if not summoner_info or 'id' not in summoner_info:
                    return f"❌ Summoner data not found for '{summoner_name}#{tag_line}'."
                
                ranked_info = self.riot_api.get_ranked_stats(summoner_info.get('id'))
                
                result = f"📊 **Summoner Profile: {summoner_name}#{tag_line}**\n\n"
                result += f"• Level: {summoner_info.get('summonerLevel', 'N/A')}\n\n"
                
                if ranked_info:
                    for queue in ranked_info:
                        queue_type = queue.get('queueType', 'Unknown')
                        tier = queue.get('tier', 'Unranked')
                        rank = queue.get('rank', '')
                        lp = queue.get('leaguePoints', 0)
                        wins = queue.get('wins', 0)
                        losses = queue.get('losses', 0)
                        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
                        
                        result += f"**{queue_type}**\n"
                        result += f"• Rank: {tier} {rank} ({lp} LP)\n"
                        result += f"• Win Rate: {wins}W / {losses}L ({win_rate:.1f}%)\n\n"
                else:
                    result += "• No ranked data available\n"
                
                return result
            except Exception as e:
                logger.error(f"Error fetching summoner profile: {e}")
                return f"❌ Error fetching summoner profile: {str(e)}"
        
        match_tools.append(get_summoner_profile)
        
        @tool
        def analyze_recent_matches(summoner_name: str = None, tag_line: str = None, num_matches: int = 10) -> str:
            """
            Analyze recent match history and provide performance insights.
            Shows KDA, win rate, CS, damage, and identifies patterns.
            """
            if summoner_name is None:
                summoner_name = self.summoner_name
            if tag_line is None:
                tag_line = get_tagline_for_summoner(summoner_name)
            
            try:
                account_info = self.riot_api.get_account_by_riot_id(summoner_name, tag_line)
                if not account_info:
                    return f"❌ Account '{summoner_name}#{tag_line}' not found."
                
                puuid = account_info.get('puuid')
                match_ids = self.riot_api.get_match_history(puuid, count=num_matches)
                
                if not match_ids:
                    return "❌ No match history found."
                
                matches_data = []
                for match_id in match_ids[:num_matches]:
                    match_detail = self.riot_api.get_match_details(match_id, puuid)
                    if match_detail:
                        matches_data.append(match_detail)
                
                if not matches_data:
                    return "❌ Could not retrieve match details."
                
                # Calculate statistics
                total_games = len(matches_data)
                wins = sum(1 for m in matches_data if m['win'])
                win_rate = (wins / total_games * 100) if total_games > 0 else 0
                
                avg_kills = sum(m['kills'] for m in matches_data) / total_games
                avg_deaths = sum(m['deaths'] for m in matches_data) / total_games
                avg_assists = sum(m['assists'] for m in matches_data) / total_games
                avg_kda = ((avg_kills + avg_assists) / avg_deaths) if avg_deaths > 0 else 0
                
                avg_cs = sum(m['cs'] for m in matches_data) / total_games
                avg_damage = sum(m['damage'] for m in matches_data) / total_games
                
                # Champion frequency
                champion_counts = {}
                for match in matches_data:
                    champ = match['champion']
                    if champ not in champion_counts:
                        champion_counts[champ] = {'games': 0, 'wins': 0}
                    champion_counts[champ]['games'] += 1
                    if match['win']:
                        champion_counts[champ]['wins'] += 1
                
                result = f"🎮 **Match Analysis: Last {total_games} Games**\n\n"
                result += f"**Overall Performance:**\n"
                result += f"• Win Rate: {wins}W / {total_games - wins}L ({win_rate:.1f}%)\n"
                result += f"• Average KDA: {avg_kills:.1f} / {avg_deaths:.1f} / {avg_assists:.1f} ({avg_kda:.2f} ratio)\n"
                result += f"• Average CS: {avg_cs:.0f}\n"
                result += f"• Average Damage: {avg_damage:,.0f}\n\n"
                
                result += "**Champion Pool:**\n"
                for champ, stats in sorted(champion_counts.items(), key=lambda x: x[1]['games'], reverse=True):
                    champ_wr = (stats['wins'] / stats['games'] * 100) if stats['games'] > 0 else 0
                    result += f"• {champ}: {stats['games']} games, {stats['wins']}W ({champ_wr:.0f}% WR)\n"
                
                result += "\n**Recent Matches:**\n"
                for i, match in enumerate(matches_data[:5], 1):
                    result_icon = "✅" if match['win'] else "❌"
                    kda = f"{match['kills']}/{match['deaths']}/{match['assists']}"
                    result += f"{i}. {result_icon} {match['champion']} - {kda} - {match['cs']} CS\n"
                
                return result
            except Exception as e:
                logger.error(f"Error analyzing matches: {e}")
                return f"❌ Error analyzing matches: {str(e)}"
        
        match_tools.append(analyze_recent_matches)
        
        # === KNOWLEDGE BASE TOOLS ===
        knowledge_tools = []
        
        # Add FAISS knowledge base search
        if self.knowledge_retriever:
            @tool
            def search_lol_knowledge(query: str) -> str:
                """
                Search the League of Legends knowledge base for information about champions,
                items, runes, game mechanics, strategies, and meta information.
                """
                try:
                    docs = self.knowledge_retriever.invoke(query)
                    if docs:
                        results = []
                        for i, doc in enumerate(docs, 1):
                            results.append(f"[Source {i}]\n{doc.page_content}\n")
                        return "\n".join(results)
                    else:
                        return "No relevant information found in the knowledge base."
                except Exception as e:
                    logger.error(f"Error searching knowledge base: {e}")
                    return f"Error searching knowledge base: {str(e)}"
            
            knowledge_tools.append(search_lol_knowledge)
        
        # Add Tavily web search for real-time LoL information
        if self.tavily_client:
            @tool
            def search_web_lol_info(query: str) -> str:
                """
                Search the web for real-time League of Legends information including:
                - Current meta analysis and tier lists
                - Latest patch notes and balance changes
                - Pro player builds and strategies
                - Champion guides from popular sites
                - Recent tournament results
                
                Use this for up-to-date information that may not be in the knowledge base.
                """
                try:
                    # Add "League of Legends" to the query for better results
                    search_query = f"League of Legends {query}"
                    logger.info(f"Tavily search: {search_query}")
                    
                    response = self.tavily_client.search(
                        query=search_query,
                        search_depth="advanced",
                        max_results=5
                    )
                    
                    if not response or 'results' not in response:
                        return "❌ No web results found."
                    
                    results = []
                    for i, result in enumerate(response['results'][:5], 1):
                        title = result.get('title', 'No title')
                        content = result.get('content', 'No content')
                        url = result.get('url', 'No URL')
                        
                        results.append(f"**[{i}] {title}**\n{content}\n🔗 Source: {url}\n")
                    
                    if results:
                        return "🌐 **Web Search Results:**\n\n" + "\n".join(results)
                    else:
                        return "❌ No relevant web results found."
                        
                except Exception as e:
                    logger.error(f"Error searching web with Tavily: {e}")
                    return f"❌ Error searching web: {str(e)}"
            
            knowledge_tools.append(search_web_lol_info)
        
        # === VIDEO GUIDE TOOLS ===
        video_tools = []
        
        @tool
        def find_champion_guides(champion_name: str, max_results: int = 5) -> str:
            """
            Find YouTube video guides for a specific champion.
            Returns video titles, channels, durations, and links to helpful guides.
            """
            try:
                query = f"League of Legends {champion_name} guide season 14 2024"
                videos = self.youtube_scraper.search_videos(query, max_results)
                
                if not videos:
                    return f"❌ No guide videos found for {champion_name}."
                
                result = f"🎬 **YouTube Guides for {champion_name}**\n\n"
                result += f"Found {len(videos)} helpful guides:\n\n"
                result += self.youtube_scraper.format_video_list(videos)
                result += "\n💡 **Tip:** Watch these guides to learn optimal combos, positioning, and decision-making!"
                
                return result
            except Exception as e:
                logger.error(f"Error finding champion guides: {e}")
                return f"❌ Error finding champion guides: {str(e)}"
        
        video_tools.append(find_champion_guides)
        
        @tool
        def find_matchup_videos(champion_name: str, enemy_champion: str, max_results: int = 3) -> str:
            """
            Find YouTube videos showing how to play a specific matchup.
            Shows real gameplay examples of your champion vs enemy champion.
            """
            try:
                query = f"League of Legends {champion_name} vs {enemy_champion} matchup guide"
                videos = self.youtube_scraper.search_videos(query, max_results)
                
                if not videos:
                    return f"❌ No matchup videos found for {champion_name} vs {enemy_champion}."
                
                result = f"⚔️ **{champion_name} vs {enemy_champion} - Matchup Videos**\n\n"
                result += f"Watch these to learn how to play this matchup:\n\n"
                result += self.youtube_scraper.format_video_list(videos)
                result += f"\n💡 **Watch for:** Trading patterns, wave management, powerspikes, and how to exploit {enemy_champion}'s weaknesses"
                
                return result
            except Exception as e:
                logger.error(f"Error finding matchup videos: {e}")
                return f"❌ Error finding matchup videos: {str(e)}"
        
        video_tools.append(find_matchup_videos)
        
        @tool
        def find_educational_videos(topic: str, max_results: int = 5) -> str:
            """
            Find educational League of Legends videos on a specific topic.
            Topics can include: wave management, trading, macro, team fighting, vision control, etc.
            """
            try:
                query = f"League of Legends {topic} guide tutorial"
                videos = self.youtube_scraper.search_videos(query, max_results)
                
                if not videos:
                    return f"❌ No educational videos found for '{topic}'."
                
                result = f"📚 **Learning Resources: {topic}**\n\n"
                result += self.youtube_scraper.format_video_list(videos)
                result += f"\n🎓 **Study tip:** Take notes while watching and practice these concepts in your next games!"
                
                return result
            except Exception as e:
                logger.error(f"Error finding educational videos: {e}")
                return f"❌ Error finding educational videos: {str(e)}"
        
        video_tools.append(find_educational_videos)
        
        # === BUILD ADVISOR TOOLS ===
        build_tools = []
        
        @tool
        def get_optimal_build(champion_name: str, role: str = "any", enemy_matchup: str = None) -> str:
            """
            Get optimal item build, runes, and skill order for a champion based on current meta.
            Uses real-time data from Tavily to find the best builds being used by high-elo players.
            """
            try:
                if not self.tavily_client:
                    return "❌ Tavily API not configured. Cannot fetch build recommendations."
                
                # Build search query
                query = f"{champion_name} {role} build items runes skill order season 14 2024 high elo pro"
                if enemy_matchup:
                    query += f" vs {enemy_matchup}"
                
                logger.info(f"Fetching optimal build: {query}")
                
                response = self.tavily_client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5
                )
                
                if not response or 'results' not in response:
                    return f"❌ Could not find build information for {champion_name}."
                
                result = f"🛠️ **Optimal Build for {champion_name}**"
                if role and role != "any":
                    result += f" ({role.capitalize()})"
                if enemy_matchup:
                    result += f" vs {enemy_matchup}"
                result += "\n\n"
                
                result += "**Current Meta Build Information:**\n\n"
                for i, item in enumerate(response['results'][:3], 1):
                    result += f"{i}. **{item['title']}**\n"
                    result += f"   {item['content'][:250]}...\n"
                    result += f"   🔗 Source: {item['url']}\n\n"
                
                result += "💡 **Tip:** Look for common patterns across sources - consistent recommendations indicate proven strategies!"
                
                return result
            except Exception as e:
                logger.error(f"Error fetching optimal build: {e}")
                return f"❌ Error fetching build: {str(e)}"
        
        build_tools.append(get_optimal_build)
        
        @tool
        def get_champion_matchups(champion_name: str) -> str:
            """
            Get matchup information including counters, favorable matchups, and tips.
            Uses real-time data to find current meta matchup analysis.
            """
            try:
                if not self.tavily_client:
                    return "❌ Tavily API not configured. Cannot fetch matchup data."
                
                query = f"{champion_name} counters matchups tier list strong against weak against"
                logger.info(f"Fetching matchup data: {query}")
                
                response = self.tavily_client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5
                )
                
                if not response or 'results' not in response:
                    return f"❌ Could not find matchup information for {champion_name}."
                
                result = f"⚔️ **{champion_name} Matchup Analysis**\n\n"
                result += "**Current Meta Analysis:**\n\n"
                
                for i, item in enumerate(response['results'][:3], 1):
                    result += f"{i}. **{item['title']}**\n"
                    result += f"   {item['content'][:250]}...\n"
                    result += f"   🔗 {item['url']}\n\n"
                
                result += "💡 **Tip:** Study your hardest matchups and learn how pros play them!"
                
                return result
            except Exception as e:
                logger.error(f"Error fetching matchups: {e}")
                return f"❌ Error fetching matchups: {str(e)}"
        
        build_tools.append(get_champion_matchups)
        
        @tool
        def get_personalized_build_advice(champion_name: str, summoner_name: str = None) -> str:
            """
            Get personalized build recommendations based on the summoner's match history and playstyle.
            Analyzes recent performance to suggest build adaptations.
            """
            try:
                # Get summoner's recent matches to analyze playstyle
                summoner_context = ""
                if summoner_name or self.summoner_name:
                    name = summoner_name or self.summoner_name
                    tagline = self.get_tagline_for_summoner(name)
                    
                    logger.info(f"Analyzing {name}'s playstyle for personalized build")
                    
                    summoner_info = self.riot_api.get_summoner(name, tagline)
                    if summoner_info and 'puuid' in summoner_info:
                        matches = self.riot_api.get_match_history(summoner_info['puuid'], count=5)
                        
                        if matches:
                            # Analyze playstyle from recent matches
                            total_kills = 0
                            total_deaths = 0
                            total_damage = 0
                            game_count = 0
                            
                            for match_id in matches[:5]:
                                match_detail = self.riot_api.get_match_details(match_id, summoner_info['puuid'])
                                if match_detail:
                                    total_kills += match_detail.get('kills', 0)
                                    total_deaths += match_detail.get('deaths', 0)
                                    total_damage += match_detail.get('damage', 0)
                                    game_count += 1
                            
                            if game_count > 0:
                                avg_kda = ((total_kills) / total_deaths) if total_deaths > 0 else total_kills
                                avg_damage = total_damage / game_count
                                
                                if avg_kda > 4:
                                    summoner_context = f"\n**Your Playstyle:** Aggressive carry-style (KDA: {avg_kda:.1f}). Consider damage-focused builds."
                                elif avg_kda < 2:
                                    summoner_context = f"\n**Your Playstyle:** Struggling with deaths (KDA: {avg_kda:.1f}). Consider defensive/survivability items."
                                else:
                                    summoner_context = f"\n**Your Playstyle:** Balanced playstyle (KDA: {avg_kda:.1f}). Standard meta builds work well."
                                
                                if avg_damage > 20000:
                                    summoner_context += f"\n**Damage Profile:** High damage dealer ({avg_damage:,.0f} avg). Keep prioritizing damage."
                                elif avg_damage < 12000:
                                    summoner_context += f"\n**Damage Profile:** Lower damage output ({avg_damage:,.0f} avg). Focus on damage items and positioning."
                
                # Get meta build with personalized context
                if not self.tavily_client:
                    return "❌ Tavily API not configured."
                
                query = f"{champion_name} build recommendations playstyle adaptations when ahead when behind"
                logger.info(f"Fetching personalized build advice: {query}")
                
                response = self.tavily_client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=4
                )
                
                result = f"🎯 **Personalized Build Advice for {champion_name}**\n"
                result += summoner_context
                result += "\n\n**Build Adaptations:**\n\n"
                
                if response and 'results' in response:
                    for i, item in enumerate(response['results'][:3], 1):
                        result += f"{i}. **{item['title']}**\n"
                        result += f"   {item['content'][:200]}...\n"
                        result += f"   🔗 {item['url']}\n\n"
                
                result += "\n💡 **Remember:** Adapt your build based on game state - build defensively when behind, offensively when ahead!"
                
                return result
            except Exception as e:
                logger.error(f"Error getting personalized build advice: {e}")
                return f"❌ Error: {str(e)}"
        
        build_tools.append(get_personalized_build_advice)
        
        # === PREGAME STRATEGY TOOLS ===
        pregame_tools = []
        
        @tool
        def recommend_bans(enemy_picks: str = None, your_role: str = None) -> str:
            """
            Recommend champions to ban based on current meta and enemy team picks.
            Helps you ban OP champions or counter enemy team composition.
            
            Args:
                enemy_picks: Comma-separated list of champions enemy has already picked (optional)
                your_role: Your intended role to ban lane counters (optional)
            """
            try:
                if not self.tavily_client:
                    return "❌ Tavily API not configured. Cannot fetch ban recommendations."
                
                # Build query based on context
                query = "League of Legends season 14 2024 best bans meta OP champions tier list"
                if enemy_picks:
                    query += f" synergy with {enemy_picks}"
                if your_role:
                    query += f" {your_role} lane counters"
                
                logger.info(f"Fetching ban recommendations: {query}")
                
                response = self.tavily_client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5
                )
                
                if not response or 'results' not in response:
                    return "❌ Could not fetch ban recommendations."
                
                result = "🚫 **Ban Recommendations**\n\n"
                
                if enemy_picks:
                    result += f"**Enemy Picks:** {enemy_picks}\n"
                if your_role:
                    result += f"**Your Role:** {your_role}\n"
                
                result += "\n**Meta Analysis & Ban Priority:**\n\n"
                
                for i, item in enumerate(response['results'][:4], 1):
                    result += f"{i}. **{item['title']}**\n"
                    result += f"   {item['content'][:220]}...\n"
                    result += f"   🔗 {item['url']}\n\n"
                
                result += "💡 **Ban Strategy Tips:**\n"
                result += "• Ban champions that counter your main champion\n"
                result += "• Ban meta OP champions with high win rates\n"
                result += "• Ban champions that synergize well with enemy picks\n"
                result += "• Consider banning champions your team struggles against"
                
                return result
            except Exception as e:
                logger.error(f"Error recommending bans: {e}")
                return f"❌ Error: {str(e)}"
        
        pregame_tools.append(recommend_bans)
        
        @tool
        def suggest_champion_pick(
            role: str,
            team_picks: str = None,
            enemy_picks: str = None,
            preferred_playstyle: str = None
        ) -> str:
            """
            Suggest the best champion to pick for your role based on team composition and enemy picks.
            
            Args:
                role: Your role (top, jungle, mid, adc, support)
                team_picks: Comma-separated list of what your team has picked (optional)
                enemy_picks: Comma-separated list of enemy team picks (optional)
                preferred_playstyle: Your preferred playstyle (aggressive, defensive, utility, etc.)
            """
            try:
                if not self.tavily_client:
                    return "❌ Tavily API not configured."
                
                # Build comprehensive query
                query = f"League of Legends best {role} champions season 14 2024"
                
                context_parts = []
                if team_picks:
                    context_parts.append(f"team composition {team_picks}")
                if enemy_picks:
                    context_parts.append(f"counter picks against {enemy_picks}")
                if preferred_playstyle:
                    context_parts.append(f"{preferred_playstyle} playstyle")
                
                if context_parts:
                    query += " " + " ".join(context_parts)
                
                query += " meta tier list synergy"
                
                logger.info(f"Suggesting champion pick: {query}")
                
                response = self.tavily_client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5
                )
                
                if not response or 'results' not in response:
                    return f"❌ Could not find champion recommendations for {role}."
                
                result = f"🎯 **Champion Pick Recommendation for {role.upper()}**\n\n"
                
                if team_picks:
                    result += f"**Your Team:** {team_picks}\n"
                if enemy_picks:
                    result += f"**Enemy Team:** {enemy_picks}\n"
                if preferred_playstyle:
                    result += f"**Playstyle:** {preferred_playstyle}\n"
                
                result += "\n**Top Recommendations:**\n\n"
                
                for i, item in enumerate(response['results'][:4], 1):
                    result += f"{i}. **{item['title']}**\n"
                    result += f"   {item['content'][:220]}...\n"
                    result += f"   🔗 {item['url']}\n\n"
                
                result += "💡 **Pick Strategy:**\n"
                result += "✓ Pick champions that synergize with your team\n"
                result += "✓ Pick counter-picks when possible\n"
                result += "✓ Pick champions you're comfortable playing\n"
                result += "✓ Consider team needs (AP/AD damage, tankiness, engage/disengage)"
                
                return result
            except Exception as e:
                logger.error(f"Error suggesting champion pick: {e}")
                return f"❌ Error: {str(e)}"
        
        pregame_tools.append(suggest_champion_pick)
        
        @tool
        def analyze_team_composition(
            your_team: str,
            enemy_team: str = None
        ) -> str:
            """
            Analyze team composition to identify win conditions, strengths, weaknesses, and strategy.
            
            Args:
                your_team: Comma-separated list of your team's champions (e.g., "Darius, Lee Sin, Ahri, Jinx, Thresh")
                enemy_team: Comma-separated list of enemy champions (optional)
            """
            try:
                if not self.tavily_client:
                    return "❌ Tavily API not configured."
                
                # Analyze team comp
                query = f"League of Legends team composition analysis {your_team}"
                if enemy_team:
                    query += f" vs {enemy_team} matchup"
                query += " win condition strategy strengths weaknesses"
                
                logger.info(f"Analyzing team composition: {query}")
                
                response = self.tavily_client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5
                )
                
                result = f"📊 **Team Composition Analysis**\n\n"
                result += f"**Your Team:** {your_team}\n"
                if enemy_team:
                    result += f"**Enemy Team:** {enemy_team}\n"
                
                result += "\n**Composition Analysis:**\n\n"
                
                if response and 'results' in response:
                    for i, item in enumerate(response['results'][:3], 1):
                        result += f"{i}. **{item['title']}**\n"
                        result += f"   {item['content'][:220]}...\n"
                        result += f"   🔗 {item['url']}\n\n"
                
                # Add basic analysis framework
                result += "\n**Key Strategic Considerations:**\n\n"
                result += "🎯 **Win Conditions:**\n"
                result += "• Identify your team's power spikes (early/mid/late game)\n"
                result += "• Determine primary win condition (team fights, split push, pick potential)\n\n"
                
                result += "💪 **Strengths to Leverage:**\n"
                result += "• Team fight potential\n"
                result += "• Engage/disengage capability\n"
                result += "• Damage type balance (AP/AD/True)\n"
                result += "• Tankiness and peel for carries\n\n"
                
                result += "⚠️ **Weaknesses to Cover:**\n"
                result += "• Lack of engage or disengage\n"
                result += "• Vulnerability to certain damage types\n"
                result += "• Poor scaling or weak early game\n"
                result += "• Limited crowd control\n\n"
                
                result += "📋 **Game Plan:**\n"
                if enemy_team:
                    result += "• Compare power spikes with enemy team\n"
                    result += "• Identify favorable and unfavorable matchups\n"
                result += "• Play to your strengths and cover weaknesses\n"
                result += "• Coordinate objectives around your win condition"
                
                return result
            except Exception as e:
                logger.error(f"Error analyzing team composition: {e}")
                return f"❌ Error: {str(e)}"
        
        pregame_tools.append(analyze_team_composition)
        
        @tool
        def get_match_team_details(summoner_name: str = None, match_number: int = 1) -> str:
            """
            Get complete team composition details from a recent match, including all 10 players,
            their champions, roles, and team assignments. Perfect for analyzing actual team comps.
            
            Args:
                summoner_name: Summoner name to get match history from (uses primary summoner if not provided)
                match_number: Which recent match to analyze (1 = most recent, 2 = second most recent, etc.)
            """
            try:
                # Determine which summoner to use
                name = summoner_name or self.summoner_name
                if not name:
                    return "❌ No summoner name provided and no default summoner configured."
                
                tagline = self.get_tagline_for_summoner(name)
                logger.info(f"Fetching match team details for {name}#{tagline}, match #{match_number}")
                
                # Get summoner info
                summoner_info = self.riot_api.get_summoner(name, tagline)
                if not summoner_info or 'puuid' not in summoner_info:
                    return f"❌ Could not find summoner: {name}#{tagline}"
                
                puuid = summoner_info['puuid']
                
                # Get match history
                matches = self.riot_api.get_match_history(puuid, count=max(match_number, 5))
                if not matches or len(matches) < match_number:
                    return f"❌ Could not retrieve match #{match_number}. Only {len(matches) if matches else 0} matches available."
                
                # Get the specific match
                match_id = matches[match_number - 1]
                logger.info(f"Analyzing match: {match_id}")
                
                # Get full match data using Riot API (without puuid to get all participants)
                match_data = self.riot_api.get_match_details(match_id)
                if not match_data or 'info' not in match_data:
                    return f"❌ Could not retrieve match data for match #{match_number}"
                
                info = match_data['info']
                participants = info.get('participants', [])
                
                if not participants:
                    return "❌ No participant data available for this match."
                
                # Find the summoner's team
                summoner_team_id = None
                for p in participants:
                    if p.get('puuid') == puuid:
                        summoner_team_id = p.get('teamId')
                        break
                
                # Organize teams
                blue_team = []
                red_team = []
                
                for p in participants:
                    player_info = {
                        'name': f"{p.get('riotIdGameName', 'Unknown')}#{p.get('riotIdTagline', '')}",
                        'champion': p.get('championName', 'Unknown'),
                        'role': p.get('teamPosition', 'UNKNOWN').replace('UTILITY', 'SUPPORT'),
                        'kills': p.get('kills', 0),
                        'deaths': p.get('deaths', 0),
                        'assists': p.get('assists', 0),
                        'win': p.get('win', False)
                    }
                    
                    if p.get('teamId') == 100:  # Blue side
                        blue_team.append(player_info)
                    else:  # Red side
                        red_team.append(player_info)
                
                # Sort teams by role
                role_order = {'TOP': 0, 'JUNGLE': 1, 'MIDDLE': 2, 'BOTTOM': 3, 'SUPPORT': 4, 'UNKNOWN': 5}
                blue_team.sort(key=lambda x: role_order.get(x['role'], 5))
                red_team.sort(key=lambda x: role_order.get(x['role'], 5))
                
                # Determine which team was yours
                your_team_label = "Blue Team" if summoner_team_id == 100 else "Red Team"
                enemy_team_label = "Red Team" if summoner_team_id == 100 else "Blue Team"
                your_team = blue_team if summoner_team_id == 100 else red_team
                enemy_team = red_team if summoner_team_id == 100 else blue_team
                
                match_result = "Victory" if your_team[0]['win'] else "Defeat"
                
                # Build result
                result = f"🎮 **Match Team Composition - Match #{match_number}**\n\n"
                result += f"**Match ID:** {match_id}\n"
                result += f"**Result:** {match_result}\n"
                result += f"**Summoner:** {name}#{tagline}\n\n"
                
                result += f"═══════════════════════════════════\n"
                result += f"**{your_team_label} (Your Team)** {'✅' if your_team[0]['win'] else '❌'}\n"
                result += f"═══════════════════════════════════\n"
                for player in your_team:
                    kda = f"{player['kills']}/{player['deaths']}/{player['assists']}"
                    role_icon = {'TOP': '⬆️', 'JUNGLE': '🌲', 'MIDDLE': '⭐', 'BOTTOM': '🎯', 'SUPPORT': '🛡️'}.get(player['role'], '❓')
                    result += f"{role_icon} **{player['role']}**: {player['champion']}\n"
                    result += f"   Player: {player['name']} | KDA: {kda}\n"
                
                result += f"\n═══════════════════════════════════\n"
                result += f"**{enemy_team_label} (Enemy Team)** {'✅' if enemy_team[0]['win'] else '❌'}\n"
                result += f"═══════════════════════════════════\n"
                for player in enemy_team:
                    kda = f"{player['kills']}/{player['deaths']}/{player['assists']}"
                    role_icon = {'TOP': '⬆️', 'JUNGLE': '🌲', 'MIDDLE': '⭐', 'BOTTOM': '🎯', 'SUPPORT': '🛡️'}.get(player['role'], '❓')
                    result += f"{role_icon} **{player['role']}**: {player['champion']}\n"
                    result += f"   Player: {player['name']} | KDA: {kda}\n"
                
                # Create composition strings for further analysis
                your_champions = [p['champion'] for p in your_team]
                enemy_champions = [p['champion'] for p in enemy_team]
                
                result += f"\n\n💡 **Team Composition Summary:**\n"
                result += f"**Your Team:** {', '.join(your_champions)}\n"
                result += f"**Enemy Team:** {', '.join(enemy_champions)}\n\n"
                result += f"📊 You can now use `analyze_team_composition` with these exact teams for detailed strategic analysis!"
                
                return result
                
            except Exception as e:
                logger.error(f"Error getting match team details: {e}")
                return f"❌ Error retrieving match details: {str(e)}"
        
        pregame_tools.append(get_match_team_details)
        
        return {
            "match": match_tools,      # get_summoner_profile, analyze_recent_matches
            "build": build_tools,      # get_optimal_build, get_champion_matchups, get_personalized_build_advice
            "video": video_tools,      # find_champion_guides, find_matchup_videos, find_educational_videos
            "knowledge": knowledge_tools,  # search_lol_knowledge with FAISS, search_web_lol_info
            "pregame": pregame_tools     # recommend_bans, suggest_champion_pick, analyze_team_composition
        }
    
    def chat(self, user_message: str, thread_id: str = "default") -> str:
        """
        Handle a user message through the multi-agent system.
        
        Args:
            user_message: User's question or request
            thread_id: Conversation thread ID
            
        Returns:
            Response from the appropriate agent(s)
        """
        logger.info(f"Processing user query: {user_message[:100]}...")
        logger.info(f"Thread ID: {thread_id}")
        
        print("\n" + "=" * 80)
        print(f"💬 User: {user_message}")
        print("=" * 80)
        
        try:
            # 1. Route the query
            route = self.router.route(user_message)
            logger.info(f"Query routed to: {route.agent}")
            
            # 2. Handle based on routing decision
            if route.agent == "orchestrator" or route.needs_multiple_agents:
                # Use orchestrator for complex queries
                logger.info("Using orchestrator for multi-agent workflow")
                response = self.orchestrator.handle_query(user_message, thread_id)
            else:
                # Direct to specific agent
                agent = self.agents.get(route.agent)
                if agent:
                    agent_desc = self.router.get_agent_description(route.agent)
                    print(f"\n{agent_desc}")
                    logger.info(f"Invoking {route.agent}")
                    response = agent.invoke(user_message, thread_id)
                    logger.info(f"Agent {route.agent} completed successfully")
                else:
                    error_msg = f"Agent '{route.agent}' not found"
                    logger.error(error_msg)
                    response = f"❌ {error_msg}"
        
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            response = self._handle_error(e, user_message)
        
        print("\n" + "=" * 80)
        print("🤖 Response:")
        print(response)
        print("=" * 80 + "\n")
        
        logger.info(f"Response length: {len(response)} characters")
        return response
    
    def _handle_error(self, error: Exception, query: str) -> str:
        """
        Handle errors gracefully with fallback responses.
        
        Args:
            error: The exception that occurred
            query: The original user query
            
        Returns:
            User-friendly error message
        """
        error_type = type(error).__name__
        logger.error(f"Error type: {error_type}, Query: {query[:100]}")
        
        # Check for specific error types
        if "API" in str(error) or "api" in str(error).lower():
            return ("⚠️ I'm having trouble connecting to the game data services right now. "
                   "Please check your API keys and try again in a moment.")
        
        if "rate limit" in str(error).lower():
            return ("⚠️ We've hit a rate limit. Please wait a moment and try again.")
        
        if "timeout" in str(error).lower():
            return ("⚠️ The request took too long. Please try again with a simpler question.")
        
        # Generic fallback
        return (f"❌ I encountered an error: {str(error)}\n\n"
                f"💡 Try asking about:\n"
                f"   • Match analysis: 'Analyze my recent games'\n"
                f"   • Champion builds: 'What items should I build on [champion]?'\n"
                f"   • Video guides: 'Find guides for [champion]'\n"
                f"   • Game knowledge: 'What does [term] mean?'\n"
                f"   • Pre-game strategy: 'Who should I ban?'")
    
    def _fallback_response(self, query: str) -> str:
        """
        Fallback response when routing fails or query is out of scope.
        
        Args:
            query: The user's query
            
        Returns:
            Helpful fallback message
        """
        logger.warning(f"Fallback triggered for query: {query[:100]}")
        
        return ("🤔 I'm not quite sure how to help with that specific question.\n\n"
                "I specialize in:\n"
                "   🎯 **Match Analysis** - Review your recent games and performance\n"
                "   🛠️ **Build Advice** - Optimal items and runes for champions\n"
                "   🎬 **Video Guides** - Find tutorials and gameplay videos\n"
                "   📚 **Game Knowledge** - Explain League of Legends concepts\n"
                "   🎯 **Pre-game Strategy** - Champion select, bans, and drafting\n\n"
                "Try rephrasing your question or ask about one of these topics!")
    
    def get_system_info(self) -> dict:
        """Get information about the multi-agent system."""
        logger.debug("Retrieving system information")
        return {
            "agents": {
                name: agent.get_info()
                for name, agent in self.agents.items()
            },
            "router": "Active",
            "orchestrator": "Active"
        }


def create_multi_agent_coach(
    openai_api_key: str = None,
    riot_api_key: str = None,
    region: str = None,
    routing_value: str = None,
    summoner_name: str = None,
    summoner_tag: str = None,
    additional_summoners: str = None
) -> MultiAgentLoLCoach:
    """
    Create a configured multi-agent LoL coach system.
    
    Args:
        openai_api_key: OpenAI API key (loads from .env if not provided)
        riot_api_key: Riot Games API key (loads from .env if not provided)
        region: Riot API region (loads from .env if not provided)
        routing_value: Riot API routing value (loads from .env if not provided)
        summoner_name: Primary summoner name (loads from .env if not provided)
        summoner_tag: Primary summoner tag (loads from .env if not provided)
        additional_summoners: Comma-separated list of summoners (loads from .env if not provided)
        
    Returns:
        Configured MultiAgentLoLCoach instance
    """
    load_dotenv()
    
    openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    riot_api_key = riot_api_key or os.getenv("RIOT_API_KEY")
    region = region or os.getenv("REGION", "na1")
    routing_value = routing_value or os.getenv("ROUTING_VALUE", "americas")
    summoner_name = summoner_name or os.getenv("SUMMONER_NAME")
    summoner_tag = summoner_tag or os.getenv("SUMMONER_TAG")
    
    # Parse additional summoners from comma-separated string
    additional_summoners_str = additional_summoners or os.getenv("ADDITIONAL_SUMMONERS", "")
    additional_summoners_list = [s.strip() for s in additional_summoners_str.split(",") if s.strip()]
    
    return MultiAgentLoLCoach(
        openai_api_key=openai_api_key,
        riot_api_key=riot_api_key,
        region=region,
        routing_value=routing_value,
        summoner_name=summoner_name,
        summoner_tag=summoner_tag,
        additional_summoners=additional_summoners_list
    )


def create_gradio_interface(coach: MultiAgentLoLCoach):
    """
    Create a Gradio web interface for the multi-agent coach.
    
    Args:
        coach: Configured MultiAgentLoLCoach instance
        
    Returns:
        Gradio Blocks interface
    """
    import gradio as gr
    
    def chat_wrapper(message, history):
        """Wrapper for Gradio chat interface"""
        try:
            # Use message directly for processing
            response = coach.chat(message, "gradio_session")
            return response
        except Exception as e:
            logger.error(f"Gradio chat error: {str(e)}", exc_info=True)
            return f"❌ Error: {str(e)}\n\nPlease try again or rephrase your question."
    
    # Create Gradio interface
    with gr.Blocks(title="⚔️ LoL Multi-Agent Coach") as demo:
        gr.Markdown(
            """
            # ⚔️ League of Legends Multi-Agent Coach
            ### AI-Powered Coaching with 5 Specialized Agents
            
            **Available Agents:**
            - 🎯 **Pregame Agent** - Champion select, bans, draft strategy
            - 🎯 **Match Analyzer** - Game history and performance analysis
            - 🛠️ **Build Advisor** - Optimal items, runes, and champions
            - 🎬 **Video Guide** - YouTube tutorials and gameplay videos
            - 📚 **Knowledge Base** - Game concepts and terminology
            
            *The system automatically routes your question to the best agent(s)!*
            """
        )
        
        with gr.Row():
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    height=500, 
                    label="Multi-Agent Coach Chat",
                    show_label=True
                )
                msg = gr.Textbox(
                    label="Your Question",
                    placeholder="E.g., 'Who should I ban?' or 'What items should I build on Ahri?'",
                    lines=2
                )
                
                with gr.Row():
                    submit = gr.Button("Send", variant="primary", size="lg")
                    clear = gr.Button("Clear Chat", size="lg")
            
            with gr.Column(scale=1):
                gr.Markdown("### 💡 Example Questions")
                examples = gr.Examples(
                    examples=[
                        "Who should I ban in ranked?",
                        "What champion should I pick for mid lane?",
                        "Analyze my recent matches",
                        "What items should I build on Ahri?",
                        "Find Yasuo guides",
                        "What does AP mean?",
                        "I keep losing as Jinx, help me",
                        "What are good team compositions?",
                        "How do I counter Yasuo?",
                        "Show me educational videos about wave management"
                    ],
                    inputs=msg,
                    label="Click to try:"
                )
                
                gr.Markdown(
                    """
                    ### 🎯 Routing Intelligence
                    
                    The router automatically detects:
                    - **Pre-game questions** → Pregame Agent
                    - **Performance questions** → Match Analyzer
                    - **Build questions** → Build Advisor
                    - **Video requests** → Video Guide
                    - **Learning questions** → Knowledge Base
                    - **Complex questions** → Multi-agent orchestration
                    """
                )
                
                with gr.Accordion("📊 System Information", open=False):
                    sys_info = coach.get_system_info()
                    gr.JSON(value=sys_info, label="Active Agents")
        
        # Event handlers - Gradio 6.x format with role/content dictionaries
        def respond(message, history):
            """Handle chat response with proper Gradio 6.x format"""
            if not message or not message.strip():
                return history, ""
            
            bot_response = chat_wrapper(message, history)
            
            # Gradio 6.x expects list of dicts with 'role' and 'content'
            history = history or []
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": bot_response})
            
            return history, ""
        
        msg.submit(respond, [msg, chatbot], [chatbot, msg])
        submit.click(respond, [msg, chatbot], [chatbot, msg])
        clear.click(lambda: [], None, chatbot, queue=False)
    
    return demo


# Example usage
if __name__ == "__main__":
    import sys
    
    # Create the multi-agent system
    coach = create_multi_agent_coach()
    
    # Check if running with --ui flag
    if "--ui" in sys.argv or "-ui" in sys.argv:
        logger.info("Starting Gradio UI interface...")
        print("\n🚀 Launching Gradio Web Interface...")
        demo = create_gradio_interface(coach)
        demo.launch(
            share=True,
            server_name="127.0.0.1",
            server_port=7860
        )
    else:
        # CLI test mode
        # Test queries demonstrating different routing
        test_queries = [
            "Who should I ban in ranked?",  # → pregame_agent
            "Analyze my recent matches",  # → match_analyzer
            "What items should I build on Ahri?",  # → build_advisor
            "Find Yasuo guides",  # → video_guide
            "What does AP mean?",  # → knowledge_base
            "I keep losing as Jinx, help me get better",  # → orchestrator (multiple agents)
        ]
        
        print("\n" + "🧪" * 40)
        print("TESTING MULTI-AGENT SYSTEM")
        print("🧪" * 40 + "\n")
        
        for query in test_queries:
            coach.chat(query)
            print("\n")
        
        # Display system info
        print("\n" + "ℹ️" * 40)
        print("SYSTEM INFORMATION")
        print("ℹ️" * 40)
        import json
        print(json.dumps(coach.get_system_info(), indent=2))
        
        print("\n💡 Tip: Run with '--ui' flag to launch web interface:")
        print("   python multi_agent_coach.py --ui")

