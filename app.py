"""
League of Legends Multi-Agent Coach - Hugging Face Spaces Version
This is a wrapper for deploying to Hugging Face Spaces.
"""

import os
import sys

# Set environment variables from Hugging Face Secrets
# These will be available in the Hugging Face Spaces settings
if not os.getenv("OPENAI_API_KEY"):
    print("⚠️ WARNING: OPENAI_API_KEY not found in environment!")
if not os.getenv("RIOT_API_KEY"):
    print("⚠️ WARNING: RIOT_API_KEY not found in environment!")
if not os.getenv("TAVILY_API_KEY"):
    print("⚠️ WARNING: TAVILY_API_KEY not found in environment!")

# Import the main application
from multi_agent_coach import create_multi_agent_coach, create_gradio_interface

# Create the coach system
print("🚀 Initializing Multi-Agent LoL Coach System for Hugging Face...")
coach = create_multi_agent_coach()

# Create the Gradio interface
print("🎨 Creating Gradio interface...")
demo = create_gradio_interface(coach)

# Launch with Hugging Face-compatible settings
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",  # Required for Hugging Face Spaces
        server_port=7860,
        share=False  # Not needed on HF Spaces
    )
