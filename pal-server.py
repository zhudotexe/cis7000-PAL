"""
Example server for the ReDel web interface.
"""

import logging

from kani.engines.openai import OpenAIEngine

from redel.server import VizServer

engine = OpenAIEngine(model="gpt-4o", temperature=0.8, top_p=0.95)

# =====================================================
# to define default patients, see redel/pal_sessions.py
# and pal_prompts/
# =====================================================

server = VizServer(engine=engine)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server.serve()
