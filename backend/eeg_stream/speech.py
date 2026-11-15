import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

MENU_PATH = Path(__file__).resolve().parents[2] / "app" / "src" / "lib" / "communication-menu.json"
MAX_AUDIO_BYTES = 8 * 1024 * 1024

MOVE_PHRASES = {
    "Outside": "I want to go outside.",
    "Inside": "I want to move inside.",
    "Reposition": "I want to change my position.",
    "Transfer": "I need help transferring.",
    "Travel": "I want to go somewhere.",
    "Park": "I want to go to the park.",
    "Home": "I want to go home.",
    "Fresh air": "I want to get some fresh air.",
    "Garden": "I want to go to the garden.",
    "Patio": "I want to go to the patio.",
    "Go for a walk": "I want to go for a walk.",
    "Indoor walk": "I want to go for a walk indoors.",
    "Sit up": "I want to sit up.",
    "Lie down": "I want to lie down.",
    "Turn left": "I want to turn left.",
    "Turn right": "I want to turn right.",
    "Raise legs": "I want to raise my legs.",
    "Adjust pillow": "I want to adjust my pillow.",
    "To wheelchair": "I need help transferring to my wheelchair.",
    "To bed": "I need help transferring to my bed.",
    "To chair": "I need help transferring to a chair.",
    "To standing": "I need help standing up.",
    "Need assistance": "I need help transferring.",
    "Visit family": "I want to visit my family.",
    "Visit friends": "I want to visit my friends.",
    "Car ride": "I want to go for a car ride.",
    "Appointment": "I want to go to my appointment.",
    "Shop": "I want to go shopping.",
}

HELP_PHRASES = {
    "Toilet": "I need help using the toilet.",
    "Clothing": "I need help with my clothes.",
    "Hygiene": "I need help with hygiene.",
    "Comfort": "I need help getting comfortable.",
    "Eating assistance": "I need help eating.",
    "Call someone": "I need someone to be called.",
    "Need to pee": "I need to pee.",
    "Bowel movement": "I need to have a bowel movement.",
    "Help to bathroom": "I need help getting to the bathroom.",
    "Bedpan": "I need a bedpan.",
    "Urinal": "I need a urinal.",
    "Change pad": "I need my pad changed.",
    "Change clothes": "I need help changing my clothes.",
    "Too tight": "My clothes are too tight.",
    "Too hot or cold": "I am too hot or too cold.",
    "Wash face": "I need help washing my face.",
    "Brush teeth": "I need help brushing my teeth.",
    "Shower": "I need help taking a shower.",
    "Wash hands": "I need help washing my hands.",
    "Comb hair": "I need help combing my hair.",
    "Clean spill": "I need help cleaning a spill.",
    "Blanket": "I need a blanket.",
    "Pillow": "I need a pillow.",
    "Adjust temperature": "I need the temperature adjusted.",
    "Reduce noise": "I need less noise.",
    "Dim lights": "I need the lights dimmed.",
    "Rest": "I need to rest.",
    "Help eating": "I need help eating.",
    "Help drinking": "I need help drinking.",
    "Cut food": "I need help cutting my food.",
    "Bring meal": "Please bring my meal.",
    "Bring straw": "Please bring me a straw.",
    "Urgent assistance": "I need urgent assistance.",
}

SOCIAL_PHRASES = {
    "Phone call": "I want to call my family.",
    "Video call": "I want to video call my family.",
    "Send message": "I want to send my family a message.",
    "Ask for a visit": "I want my family to visit.",
    "Share an update": "I want to share an update with my family.",
    "Phone a friend": "I want to call a friend.",
    "Video call a friend": "I want to video call a friend.",
    "Message a friend": "I want to message a friend.",
    "Ask a friend to visit": "I want a friend to visit.",
    "Chat together": "I want to chat with my friends.",
    "Watch a movie": "I want to watch a movie with my friends.",
    "Listen to music": "I want to listen to music with my friends.",
    "Play a game": "I want to play a game with my friends.",
    "Go out together": "I want to go out with my friends.",
    "Hello": "Hello.",
    "Thank you": "Thank you.",
    "I miss you": "I miss you.",
    "Please visit": "Please visit.",
    "See you soon": "See you soon.",
}


def demo_phrase(path: list[int]) -> str:
    with MENU_PATH.open(encoding="utf-8") as menu_file:
        node = json.load(menu_file)
    labels = []
    for index in path:
        children = node.get("children", [])
        if index < 0 or index >= len(children):
            raise ValueError("Invalid demo menu path")
        node = children[index]
        labels.append(node["label"])

    category = labels[0]
    detail = labels[-1]
    if category in ("Food", "Drink"):
        if detail == "Other":
            return f"I would like another {category.lower()} option."
        if category == "Food" and len(labels) == 3 and labels[1] == "Soup" and detail != "Beef broth":
            return f"I want {detail.lower()} soup."
        return f"I want {detail.lower()}."
    if category == "Move":
        if len(labels) == 1:
            return "I want to move."
        if detail == "Other":
            return "I want to move somewhere else." if labels[1] in ("Outside", "Inside", "Travel") else "I want to move another way."
        if detail in MOVE_PHRASES:
            return MOVE_PHRASES[detail]
        return f"I want to go to the {detail.lower()}."
    if category == "Pain":
        if len(labels) == 1:
            return "I am in pain."
        if detail == "Other":
            return "I have pain somewhere else."
        location = {"Back of head": "the back of my head", "Top of foot": "the top of my foot"}.get(detail, f"my {detail.lower()}")
        return f"I have pain in {location}."
    if category == "Help":
        if len(labels) == 1:
            return "I need help."
        if detail == "Other":
            return "I need help with something else."
        if detail in HELP_PHRASES:
            return HELP_PHRASES[detail]
        if labels[1] == "Call someone":
            return f"Please call a {detail.lower()}."
        return f"I need help with my {detail.lower()}."
    if category == "Family":
        if len(labels) == 1:
            return "I want to contact my family."
        if detail == "Other":
            return "I want to contact another family member."
        if detail == "Contact family":
            return "I want to contact my family."
        return SOCIAL_PHRASES.get(detail, f"I want to contact my {detail.lower()}.")
    if category == "Friends":
        if len(labels) == 1:
            return "I want to contact my friends."
        if detail == "Other":
            return "I want to talk about something else with my friends."
        if detail == "Contact friends":
            return "I want to contact my friends."
        if detail == "Activities":
            return "I want to do something with my friends."
        if detail == "Messages":
            return "I want to send a message to my friends."
        if detail in SOCIAL_PHRASES:
            return SOCIAL_PHRASES[detail]
        return f"I want to contact my {detail.lower()}."
    return "I would like something else."


def synthesize_demo_speech(path: list[int]) -> bytes:
    try:
        text = demo_phrase(path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
    if not api_key or not voice_id:
        raise HTTPException(status_code=503, detail="Demo speech is not configured. Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in backend\\.env.local.")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", voice_id):
        raise HTTPException(status_code=503, detail="The configured ElevenLabs voice ID is invalid.")

    payload = json.dumps({"text": text, "model_id": "eleven_multilingual_v2"}).encode("utf-8")
    request = Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        data=payload,
        headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            if response.headers.get_content_type() != "audio/mpeg":
                raise HTTPException(status_code=502, detail="ElevenLabs returned an unexpected audio format.")
            audio = response.read(MAX_AUDIO_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 402:
            raise HTTPException(status_code=502, detail="ElevenLabs could not generate speech. Check your ElevenLabs credits and billing (HTTP 402).") from exc
        raise HTTPException(status_code=502, detail=f"ElevenLabs speech failed (HTTP {exc.code}). Check the voice, API key and account quota.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=502, detail="Could not reach ElevenLabs for demo speech.") from exc
    if not audio or len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=502, detail="ElevenLabs returned invalid or oversized audio.")
    return audio
