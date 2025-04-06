"""
Service for interacting with the ElevenLabs API to generate narrations from stories.
This is a mock implementation for the hackathon project.
"""

import asyncio
from typing import Optional

# In a real implementation, you would use the ElevenLabs API
# import elevenlabs

# Mock audio URLs to simulate ElevenLabs output
AUDIO_URLS = [
    "https://www2.cs.uic.edu/~i101/SoundFiles/StarWars3.wav",
    "https://www2.cs.uic.edu/~i101/SoundFiles/StarWars60.wav",
    "https://www2.cs.uic.edu/~i101/SoundFiles/CantinaBand3.wav",
    "https://www2.cs.uic.edu/~i101/SoundFiles/CantinaBand60.wav",
]

async def generate_narration(story: str, voice_sample_path: Optional[str] = None) -> str:
    """
    Generate an audio narration of the story using ElevenLabs API.
    
    Args:
        story: The story text to narrate
        voice_sample_path: Optional path to a voice sample for voice cloning
        
    Returns:
        URL to the generated audio file
    """
    # In a real implementation, you would call the ElevenLabs API
    # if voice_sample_path:
    #     # Clone voice from the provided sample
    #     voice_id = elevenlabs.clone_voice(voice_sample_path)
    #     audio = elevenlabs.generate_speech(story, voice_id=voice_id)
    # else:
    #     # Use a default voice
    #     audio = elevenlabs.generate_speech(story, voice_id="default")
    # 
    # # Save the audio file and return its URL
    # audio_path = f"uploads/{uuid.uuid4()}.mp3"
    # with open(audio_path, "wb") as f:
    #     f.write(audio)
    # return f"/uploads/{os.path.basename(audio_path)}"
    
    # For the hackathon, we'll use a mock implementation
    # Simulate API delay
    await asyncio.sleep(2)
    
    # Return a fixed audio URL based on whether a voice sample was provided
    if voice_sample_path:
        # Pretend we used the voice sample
        return AUDIO_URLS[0]
    else:
        # Use a "default" voice
        return AUDIO_URLS[1] 