from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient

from typing import Optional
from datetime import datetime, timezone
from pathlib import Path
import logging
import os
import re
import uuid
import json

from dotenv import load_dotenv

import assemblyai as aai
import google.generativeai as genai

from supabase import create_client, Client

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = MongoClient(MONGO_URL)
try:
    client.admin.command('ping')
    db = client.memoir
    memories_collection = db.data
    logger.info("Connected to MongoDB")
except Exception as e:
    logger.error("MongoDB connection failed: %s", e)

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# AssemblyAI setup
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

# FastAPI app init
app = FastAPI(title="Memoir AI API", description="API for the Memoir AI application")

# CORS config
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper: Upload to Supabase Storage

async def upload_audio_uploadfile(
    file: UploadFile,
    supabase: Client,
    folder: str = "audio"
) -> str:
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    try:
        # Save file position to reset it later
        original_position = file.file.tell()

        # Validate file size (example: 10MB limit)
        max_size = 100 * 1024 * 1024  # 10MB
        file.file.seek(0, 2)  # Seek to end to get size
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to start for reading
        
        if file_size > max_size:
            raise HTTPException(status_code=413, detail="File too large")

        # Read file content
        file_bytes = await file.read()
        if isinstance(file_bytes, str):
            raise ValueError("Upload file was incorrectly read as string instead of bytes.")

        # Create unique file path
        file_path = f"{folder}/{uuid.uuid4()}_{file.filename.replace(' ', '_')}"

        # Upload to Supabase
        result = supabase.storage.from_("media").upload(
            path=file_path,
            file=file_bytes,
            file_options={
                "content-type": file.content_type or "application/octet-stream"
            }
        )
        # Check if upload was successful
        if not result:
            raise HTTPException(status_code=500, detail="Failed to upload file")

        # Get public URL
        public_url = supabase.storage.from_("media").get_public_url(file_path)
        
        # Reset file position to where it was before
        await file.seek(original_position)

        return public_url

    except Exception as e:
        # Handle specific exceptions as needed
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

async def upload_video_uploadfile(
    file: UploadFile,
    supabase: Client,
    folder: str = "video"
) -> str:
    if not file:
        raise HTTPException(status_code=400, detail="No video file provided")

    try:
        # Save file position to reset it later
        original_position = file.file.tell()
        
        # Validate file size (example: 50MB limit for videos)
        max_size = 50 * 1024 * 1024  # 50MB
        file.file.seek(0, 2)  # Seek to end to get size
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to start for reading
        
        if file_size > max_size:
            raise HTTPException(status_code=413, detail="Video file too large")

        # Read file content
        file_bytes = await file.read()
        if isinstance(file_bytes, str):
            raise ValueError("Upload file was incorrectly read as string instead of bytes.")

        # Create unique file path
        file_path = f"{folder}/{uuid.uuid4()}_{file.filename.replace(' ', '_')}"

        # Upload to Supabase
        result = supabase.storage.from_("media").upload(
            path=file_path,
            file=file_bytes,
            file_options={
                "content-type": file.content_type or "video/mp4"
            }
        )

        # Check if upload was successful
        if not result:
            raise HTTPException(status_code=500, detail="Failed to upload video file")

        # Get public URL
        public_url = supabase.storage.from_("media").get_public_url(file_path)
        
        # Reset file position to where it was before
        await file.seek(original_position)
        
        return public_url

    except Exception as e:
        # Handle specific exceptions as needed
        raise HTTPException(status_code=500, detail=f"Error uploading video file: {str(e)}")

async def upload_image_uploadfile(
    file: UploadFile,
    supabase: Client,
    folder: str = "image"
) -> str:
    if not file:
        raise HTTPException(status_code=400, detail="No image file provided")

    try:
        # Save file position to reset it later
        original_position = file.file.tell()
        
        # Validate file size (example: 5MB limit for images)
        max_size = 5 * 1024 * 1024  # 5MB
        file.file.seek(0, 2)  # Seek to end to get size
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to start for reading
        
        if file_size > max_size:
            raise HTTPException(status_code=413, detail="Image file too large")

        # Read file content
        file_bytes = await file.read()
        if isinstance(file_bytes, str):
            raise ValueError("Upload file was incorrectly read as string instead of bytes.")

        # Create unique file path
        file_path = f"{folder}/{uuid.uuid4()}_{file.filename.replace(' ', '_')}"

        # Upload to Supabase
        result = supabase.storage.from_("media").upload(
            path=file_path,
            file=file_bytes,
            file_options={
                "content-type": file.content_type or "image/jpeg"
            }
        )

        # Check if upload was successful
        if not result:
            raise HTTPException(status_code=500, detail="Failed to upload image file")

        # Get public URL
        public_url = supabase.storage.from_("media").get_public_url(file_path)
        
        # Reset file position to where it was before
        await file.seek(original_position)
        
        return public_url

    except Exception as e:
        # Handle specific exceptions as needed
        raise HTTPException(status_code=500, detail=f"Error uploading image file: {str(e)}")

# Helper: Transcribe audio using AssemblyAI
async def transcribe_audio_with_assemblyai(audio_file: UploadFile) -> str:
    try:
        # Reset file position to start
        await audio_file.seek(0)
        
        # Create a temporary file path
        Path("audio").mkdir(parents=True, exist_ok=True)
        temp_filename = f"temp_{uuid.uuid4()}_{audio_file.filename}"
        file_path = os.path.join("audio", temp_filename)
        
        # Write the content to a temporary file
        with open(file_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        # Reset file position again for potential reuse
        await audio_file.seek(0)
        
        # Transcribe the audio using AssemblyAI
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(file_path)
        return transcript.text
    except Exception as e:
        logger.error("AssemblyAI transcription error: %s", e)
        return ""
    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.remove(file_path)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Memoir AI API is running"}

# ✅ Fetch all memories
@app.get("/api/memories")
async def get_all_memories():
    try:
        memories_cursor = memories_collection.find().sort("timestamp", -1)
        memories = []
        for memory in memories_cursor:
            # Convert datetime to string format
            timestamp = memory.get("timestamp")
            if timestamp and isinstance(timestamp, datetime):
                timestamp_str = timestamp.isoformat()
            else:
                timestamp_str = None
                
            memories.append({
                "id": str(memory["_id"]),
                "audioUrl": memory.get("audio", ""),
                "videoUrl": memory.get("video", ""),
                "imageUrl": memory.get("image_url", ""),
                "title": memory.get("title", "Memory"),
                "story": memory.get("story", ""),
                "tags": memory.get("tags", []),
                "timestamp": timestamp_str
            })
        return JSONResponse(content={"memories": memories}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching memories: {str(e)}")

# ✅ Create memory
@app.post("/api/memories")
async def create_memory(
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None)
):
    if not video and not audio:
        raise HTTPException(status_code=400, detail="Either audio or video must be provided")

    try:
        # Handle file uploads using specialized functions
        audio_url = await upload_audio_uploadfile(audio, supabase) if audio else None
        video_url = await upload_video_uploadfile(video, supabase) if video else None
        image_url = await upload_image_uploadfile(image, supabase) if image else None
        logger.info("Uploaded media: audio=%s video=%s image=%s", audio_url, video_url, image_url)

        # Get transcription if audio is provided
        memory_text = ""
        if audio:
            memory_text = await transcribe_audio_with_assemblyai(audio)
            logger.info("Transcribed %d characters", len(memory_text))

        # Generate story using Gemini
        system_instruction = """Take the given transcript and refine it into a polished, coherent, and engaging story. Ensure the narrative flows smoothly without adding any new information beyond what is provided in the transcript. Additionally, generate a concise and relevant title that encapsulates the essence of the story. Deliver the output in JSON format with two keys: 'title' for the story's title and 'story' for the cleaned-up narrative. Do not miss even a single detail present in the transcript."""
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            system_instruction=system_instruction
        )
        response = model.generate_content(
            contents=[memory_text or "Create a short story about a memory"],
            generation_config=genai.GenerationConfig(temperature=0.7)
        )

        # Add robust error handling for JSON parsing
        try:
            # Try to parse the response text as JSON directly
            raw_string = response.text.strip()
            
            # If the response is wrapped in backticks or markdown code blocks, clean it up
            if raw_string.startswith("```json") and raw_string.endswith("```"):
                raw_string = raw_string[7:-3].strip()
            elif raw_string.startswith("```") and raw_string.endswith("```"):
                raw_string = raw_string[3:-3].strip()
            
            # Try to parse the JSON
            try:
                parsed = json.loads(raw_string)
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract JSON-like content using regex
                json_pattern = r'\{[\s\S]*?\}'  # More robust pattern to match JSON objects
                match = re.search(json_pattern, raw_string, re.DOTALL)
                if match:
                    try:
                        parsed = json.loads(match.group(0))
                    except:
                        raise ValueError("Could not parse JSON from response")
                else:
                    raise ValueError("No JSON-like structure found in response")
            
            # Access fields with error handling
            title = parsed.get("title", "Untitled Memory")
            story = parsed.get("story", raw_string)  # Fallback to raw string if no story field
            
        except Exception as e:
            logger.warning("Error parsing story JSON, falling back to raw text: %s", e)
            title = "Memory"
            story = response.text.strip()

        # Generate tags using Gemini
        tag_instruction = """
Analyze the provided transcript and identify the emotions present in the story. You must select a maximum of three emotions from the following list:

- Joy  
- Love  
- Gratitude  
- Hope  
- Contentment  
- Surprise  
- Curiosity  
- Anger  

Do not include any emotions outside of this list. Provide your response in Text format with a single space between each emotion, listing the selected emotions.

"""
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

        # Initialize model with system instruction
        model = genai.GenerativeModel(
            'gemini-2.0-flash',
            system_instruction=tag_instruction
        )

        # Generate refined story
        response = model.generate_content(
            contents=[story],
            generation_config=genai.GenerationConfig(
                temperature=0.7
            )
        )
        tags = response.text.split()

        memory_doc = {
            "audio": audio_url,
            "video": video_url,
            "image_url": image_url,
            "title": title,
            "story": story,
            "tags": tags,
            "timestamp": datetime.now(timezone.utc)
        }

        result = memories_collection.insert_one(memory_doc)
        logger.info("Stored memory %s", result.inserted_id)

        return JSONResponse({
            "id": str(result.inserted_id),
            "title": title,
            "story": story,
            "audioUrl": audio_url,
            "videoUrl": video_url,
            "imageUrl": image_url,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing memory: {str(e)}")

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
