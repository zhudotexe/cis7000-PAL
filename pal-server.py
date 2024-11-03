"""
Example server for the ReDel web interface.
"""

import logging
from pathlib import Path

from kani.engines.openai import OpenAIEngine

from redel import ReDel
from redel.server import VizServer

engine = OpenAIEngine(model="gpt-4o", temperature=0.8, top_p=0.95)


async def startup(server):
    # NEIL STARTING PROMPTS
    # tbh this could be a for loop but I am lazy, so this is a Neil problem
    nicki_system = (Path(__file__).parent / "pal_prompts/nicki_system.txt").read_text().strip()
    nicki_info = (Path(__file__).parent / "pal_prompts/nicki_info.md").read_text().strip()
    nicki = ReDel(
        engine=engine,
        system_prompt=nicki_system,
        title="Nicki Martin, 46 F",
        extra={"patient_info": nicki_info},  # see redel/utils.py for FrontendExtra
    )
    await server.append_new_redel(nicki)

    aiden_system = (Path(__file__).parent / "pal_prompts/aiden_system.txt").read_text().strip()
    aiden_info = (Path(__file__).parent / "pal_prompts/aiden_info.md").read_text().strip()
    aiden = ReDel(
        engine=engine,
        system_prompt=aiden_system,
        title="Aiden Brown, 37 M",
        extra={"patient_info": aiden_info},
    )
    await server.append_new_redel(aiden)

    aaron_system = (Path(__file__).parent / "pal_prompts/aaron_system.txt").read_text().strip()
    aaron_info = (Path(__file__).parent / "pal_prompts/aaron_info.md").read_text().strip()
    aaron = ReDel(
        engine=engine,
        system_prompt=aaron_system,
        title="Aaron Johnson, 55 M",
        extra={"patient_info": aaron_info},
    )
    await server.append_new_redel(aaron)


server = VizServer(engine=engine, startup_fn=startup)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server.serve()
