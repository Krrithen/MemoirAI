import axios from "axios";

// Base URL for the API
const API_BASE_URL = "http://localhost:8000/api";

// Create an Axios instance with common configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// API functions
export const memoirApi = {
  // Submit a memory to be processed
  submitMemory: async (textMemory, audioFile) => {
    // Create form data to send files
    const formData = new FormData();
    formData.append("text", textMemory);

    if (audioFile) {
      formData.append("audio", audioFile.data);
    }

    // In a real implementation, this would call the actual endpoint
    // return await api.post('/memories', formData, {
    //   headers: {
    //     'Content-Type': 'multipart/form-data',
    //   },
    // });

    // For now, we'll return a mock response after a delay
    await new Promise((resolve) => setTimeout(resolve, 2000));

    return {
      data: {
        story:
          "It was a warm summer evening when you decided to take that spontaneous road trip to the coast. The windows were down, music playing, and the salty breeze welcomed you as you approached the shoreline. You remember laughing with your friends, taking pictures of the sunset, and feeling completely free. That night under the stars, sharing stories around a small bonfire, was when you realized how precious these moments are - the ones that seem so ordinary yet become the memories we treasure most.",
        imageUrl:
          "https://placehold.co/600x400/e2e8f0/475569?text=Generated+Memory+Image",
        audioUrl: "https://www2.cs.uic.edu/~i101/SoundFiles/StarWars3.wav", // Sample audio for testing
      },
    };
  },
};

export default api;
