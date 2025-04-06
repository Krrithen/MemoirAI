# Memoir AI

Memoir AI is a full-stack application that helps users record and recreate their personal memories using AI. This project was created for a hackathon to demonstrate the integration of various AI technologies.

## 🔍 Overview

Users can record or upload a memory via voice or text, which is then processed by AI to:

1. Transform the memory into a written story (using Google's Gemini API)
2. Generate an image that represents the memory (using Gemini API)
3. Narrate the story in the user's own voice (using ElevenLabs voice cloning)

## 🚀 Features

- **Memory Input**: Record audio or type your memory
- **Text Memory Processing**: Convert raw memories into polished stories
- **Memory Visualization**: Generate images that represent your memories
- **Voice Cloning**: Have your stories narrated in your own voice
- **Simple UX**: Clean, intuitive interface focused on the content

## 🛠️ Tech Stack

### Frontend

- React
- TailwindCSS
- Uppy (for audio recording/uploading)

### Backend

- Python (FastAPI)
- Integration with Gemini API (mock for now)
- Integration with ElevenLabs API (mock for now)

## 📋 Getting Started

### Prerequisites

- Node.js (v14 or higher)
- Python 3.8 or higher
- npm or yarn

### Running the Frontend

```bash
cd frontend
npm install
npm start
```

### Running the Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 🖼️ Demo

The application allows users to input memories either by text or voice recording. Once submitted, the memory is processed by AI, and three outputs are generated:

1. A polished written story based on the memory
2. An image that represents the memory
3. An audio narration of the story in a voice similar to the user's

## 🎯 Future Improvements

- **Real API Integration**: Connect to actual Gemini and ElevenLabs APIs
- **User Authentication**: Allow users to create accounts and save memories
- **Memory Timeline**: View memories in chronological order
- **Memory Sharing**: Share memories with friends and family
- **Enhanced Voice Cloning**: More accurate voice cloning with less audio required

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
