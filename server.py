"""
Example server for the ReDel web interface.
"""

import logging
import os

from kani.engines.anthropic import AnthropicEngine
from kani.engines.openai import OpenAIEngine
from kani.ext.ratelimits import RatelimitedEngine

from redel import AUTOGENERATE_TITLE, ReDel
from redel.server import VizServer

# Define the engines
engine = OpenAIEngine(model="gpt-4", temperature=0.8, top_p=0.95)
if "ANTHROPIC_API_KEY" in os.environ:
    long_engine = RatelimitedEngine(
        AnthropicEngine(model="claude-3-5-sonnet-20240620", temperature=0.7, max_tokens=4096), max_concurrency=1
    )
else:
    long_engine = None

# Define the configuration for each interactive session
ai = ReDel(engine=engine, title=AUTOGENERATE_TITLE)

# configure and start the server
server = VizServer(ai)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server.serve()
