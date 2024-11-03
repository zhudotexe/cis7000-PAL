"""
Example server for the ReDel web interface.
"""

import logging
from pathlib import Path

from kani.engines.openai import OpenAIEngine

from redel import ReDel
from redel.server import VizServer

engine = OpenAIEngine(model="gpt-4o", temperature=0.8, top_p=0.95)
server = VizServer(engine=engine)

# NEIL STARTING PROMPTS
nicki_system = (Path(__file__).parent / "pal_prompts/nicki_system.txt").read_text().strip()
nicki_info = (Path(__file__).parent / "pal_prompts/nicki_info.md").read_text().strip()
nicki = ReDel(
    engine=engine,
    system_prompt=nicki_system,
    title="Nicki Martin, 46 F",
    extra={"patient_info": nicki_info},  # see redel/utils.py for FrontendExtra
)
server.append_new_redel(nicki)

aiden_system = (Path(__file__).parent / "pal_prompts/aiden_system.txt").read_text().strip()
aiden_info = (Path(__file__).parent / "pal_prompts/aiden_info.md").read_text().strip()
aiden = ReDel(
    engine=engine,
    system_prompt=aiden_system,
    title="Aiden Brown, 37 M",
    extra={"patient_info": aiden_info},
)
server.append_new_redel(nicki)

aaron_system = (Path(__file__).parent / "pal_prompts/aaron_system.txt").read_text().strip()
aaron_info = (Path(__file__).parent / "pal_prompts/aaron_info.md").read_text().strip()
aaron = ReDel(
    engine=engine,
    system_prompt=aaron_system,
    title="Aaron Johnson, 55 M",
    extra={"patient_info": aaron_info},
)
server.append_new_redel(nicki)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server.serve()
