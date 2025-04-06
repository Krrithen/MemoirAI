"""
Service for interacting with the Gemini API to generate stories and images from memories.
This is a mock implementation for the hackathon project.
"""

import asyncio
import random

# In a real implementation, you would use the Google Gemini API
# import google.generativeai as genai

# Mock story templates to simulate Gemini output
STORY_TEMPLATES = [
    "It was a warm summer evening when {memory_hint}. The air was filled with the scent of jasmine, and the sky painted with hues of orange and pink. You remember laughing, feeling completely at peace with the world around you. In those moments, time seemed to stand still, creating a memory that would stay with you forever.",
    
    "Winter had just arrived when {memory_hint}. Snowflakes danced in the air as they made their way to the ground, covering everything in a pristine white blanket. The cold was biting, but there was warmth in the connections you forged that day. Looking back, this memory feels like it's wrapped in the comfort of a favorite blanket.",
    
    "The city lights twinkled below as {memory_hint}. From that height, everything seemed so small, so manageable. You remember feeling on top of the world, literally and figuratively. It's funny how some memories stay so vivid - the sounds, the smells, the exact way the light hit your face. This was one of those perfect moments that remind you why life is worth living.",
    
    "The old family kitchen was filled with the aroma of spices when {memory_hint}. Generations of recipes and stories were exchanged over simmering pots and freshly baked bread. These traditions, passed down through time, became more than just cooking lessons; they were moments of connection, of understanding where you came from and who you might become.",
]

# Mock image URLs to simulate Gemini image generation
IMAGE_URLS = [
    "https://placehold.co/600x400/e2e8f0/475569?text=Memory+Visualization+1",
    "https://placehold.co/600x400/f8fafc/1e293b?text=Memory+Visualization+2",
    "https://placehold.co/600x400/f1f5f9/334155?text=Memory+Visualization+3",
    "https://placehold.co/600x400/f9fafb/111827?text=Memory+Visualization+4",
]

async def generate_story(memory_text: str) -> str:
    """
    Generate a story based on the memory text using Gemini API.
    
    Args:
        memory_text: The user's memory in text form
        
    Returns:
        A generated story based on the memory
    """
    # In a real implementation, you would call the Gemini API
    # response = genai.generate_text(f"Transform this memory into a descriptive, emotional story: {memory_text}")
    
    # For the hackathon, we'll use a mock implementation
    # Extract a hint from the memory text to personalize the story
    memory_hint = memory_text[:50] + "..." if len(memory_text) > 50 else memory_text
    
    # Simulate API delay
    await asyncio.sleep(1)
    
    # Return a random story template with the memory hint inserted
    return random.choice(STORY_TEMPLATES).format(memory_hint=memory_hint.lower())

async def generate_image(story: str) -> str:
    """
    Generate an image based on the story using Gemini API.
    
    Args:
        story: The generated story text
        
    Returns:
        URL to the generated image
    """
    # In a real implementation, you would call the Gemini API 
    # response = genai.generate_image(f"Create an artistic visualization of this story: {story}")
    
    # For the hackathon, we'll use a mock implementation
    # Simulate API delay
    await asyncio.sleep(1.5)
    
    # Return a random image URL from our mock collection
    return random.choice(IMAGE_URLS) 