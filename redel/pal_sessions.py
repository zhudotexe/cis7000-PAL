import time
import uuid
from pathlib import Path

from typing_extensions import TypedDict

from redel.app import ReDel
from redel.config import DEFAULT_LOG_DIR

PAL_PROMPTS = Path(__file__).parents[1] / "pal_prompts"


class FrontendExtra(TypedDict, total=False):
    """Extra information to send to the frontend. All value types must be JSON serializable."""

    patient_info: str
    patient_image_url: str
    patient_voice: str
    patient_name: str
    patient_age: str
    patient_gender: str


async def get_default_sessions(engine, uid: str) -> list[ReDel]:
    redels = []
    now = int(time.time())

    # NEIL STARTING PROMPTS
    # tbh this could be a for loop but I am lazy, so this is a Neil problem
    session_id = f"{now}-nicki-{uuid.uuid4()}"
    log_dir = DEFAULT_LOG_DIR / uid / session_id
    nicki_system = (PAL_PROMPTS / "nicki_system.txt").read_text().strip()
    nicki_info = (PAL_PROMPTS / "nicki_info.md").read_text().strip()
    nicki = ReDel(
        engine=engine,
        session_id=session_id,
        log_dir=log_dir,
        system_prompt=nicki_system,
        title="Nicki Martin, 46 F",
        extra={
            "patient_info": nicki_info,
            "patient_name": "Nicki Martin",
            "patient_age": "46",
            "patient_gender": "F",
            "patient_image_url": "/faces/nicki_martin.png",
            "patient_voice": "ug7mg45jVbzgYHpQBrw5",
        },
    )
    redels.append(nicki)

    session_id = f"{now}-aiden-{uuid.uuid4()}"
    log_dir = DEFAULT_LOG_DIR / uid / session_id
    aiden_system = (PAL_PROMPTS / "aiden_system.txt").read_text().strip()
    aiden_info = (PAL_PROMPTS / "aiden_info.md").read_text().strip()
    aiden = ReDel(
        engine=engine,
        session_id=session_id,
        log_dir=log_dir,
        system_prompt=aiden_system,
        title="Aiden Brown, 37 M",
        extra={
            "patient_info": aiden_info,
            "patient_name": "Aiden Brown",
            "patient_age": "37",
            "patient_gender": "M",
            "patient_image_url": "/faces/aiden_brown.png",
            "patient_voice": "Alex",
        },
    )
    redels.append(aiden)

    session_id = f"{now}-aaron-{uuid.uuid4()}"
    log_dir = DEFAULT_LOG_DIR / uid / session_id
    aaron_system = (PAL_PROMPTS / "aaron_system.txt").read_text().strip()
    aaron_info = (PAL_PROMPTS / "aaron_info.md").read_text().strip()
    aaron = ReDel(
        engine=engine,
        session_id=session_id,
        log_dir=log_dir,
        system_prompt=aaron_system,
        title="Aaron Johnson, 55 M",
        extra={
            "patient_info": aaron_info,
            "patient_name": "Aaron Johnson",
            "patient_age": "55",
            "patient_gender": "M",
            "patient_image_url": "/faces/aaron_johnson.png",
            "patient_voice": "Edward",
        },
    )
    redels.append(aaron)

    return redels
