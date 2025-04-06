import React, { useState } from "react";
import MemoryDisplay from "./components/MemoryDisplay";
import MemoriesGallery from "./components/MemoriesGallery";
import MediaUpload from "./components/MediaUpload";
import VoiceRecorder from "./components/VoiceRecorder";
import ElevenLabsConvai from "./components/ElevenLabsConvai";
import memoirLogo from "./MemoirAI.png";
import "./index.css";

function App() {
  const [memory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [mediaFile, setMediaFile] = useState(null);
  const [audioBlob, setAudioBlob] = useState(null);

  const handleMemorySubmit = async () => {
    setLoading(true);
    try {
      const formData = new FormData();

      if (mediaFile) {
        if (mediaFile.type.startsWith("video")) {
          formData.append("video", mediaFile);
        } else if (mediaFile.type.startsWith("image")) {
          formData.append("image", mediaFile);
        } else {
          console.warn("Unsupported media type:", mediaFile.type);
        }
      }

      if (audioBlob) {
        const audioFile = new File([audioBlob], "recording.wav", {
          type: "audio/wav",
        });
        formData.append("audio", audioFile);
      }

      const response = await fetch("http://127.0.0.1:8000/api/memories", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Failed with status ${response.status}`);
      }

      alert("✅ Memory uploaded successfully!");
    } catch (error) {
      console.error("Error uploading memory:", error);
      alert("❌ There was an error uploading your memory.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Main Layout */}
      <div className="flex h-screen overflow-hidden">
        {/* Left Section (Fixed, non-scrollable) */}
        <div className="w-1/4 p-6 relative bg-[#0a0f1c] text-white">
          <div
            className="absolute top-0 left-0 w-75 h-75 rounded-full opacity-30 blur-3xl z-0"
            style={{
              backgroundColor: "#0a0f1c",
            }}
          ></div>

          {/* Foreground Content */}
          <div className="relative z-10 h-full">
            {memory ? (
              <MemoryDisplay memory={memory} />
            ) : (
              <div className="text-center text-gray-300 mt-20 space-y-4">
                <img
                  src={memoirLogo}
                  alt="Memoir AI Logo"
                  className="mx-auto w-48 h-48 mb-2 mt-0"
                />
                <h1 className="text-1xl md:text-2xl lg:text-3xl font-semibold leading-tight tracking-wide text-white">
                  Your Personalized AI with Memories
                </h1>
                <p className="text-sm md:text-base lg:text-lg font-light text-gray-400 max-w-xs mx-auto">
                  An AI that remembers everything — built from the life you've
                  lived.
                </p>
                <ul className="text-sm md:text-base text-gray-300 pt-6 pb-5 space-y-2 list-none">
                  <li>📸 Upload a photo or video</li>
                  <li>🎙️ Record or upload your voice</li>
                  <li>🧠 Our AI processes your memories</li>
                  <li>❤️ Relive your memories!</li>
                </ul>
                <div className="pt-2 w-full max-w-md mx-auto">
                  <ElevenLabsConvai />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Section (Scrollable) */}
        <div className="w-3/4 h-screen overflow-y-auto p-4 bg-[#0a0f1c] shadow-xl">
          <div className="max-w-7xl mx-auto flex-grow">
            {memory ? <MemoryDisplay memory={memory} /> : <MemoriesGallery />}
          </div>
        </div>
      </div>

      {/* Floating Create Memory Button */}
      <button
        onClick={() => setShowModal(true)}
        className="fixed bottom-6 right-6 bg-blue-500 text-white px-5 py-3 rounded-full shadow-lg hover:bg-blue-700 transition z-50"
      >
        + Create Memory
      </button>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-40">
          <div className="w-3/5 bg-white p-8 rounded-xl shadow-xl relative">
            <h2 className="text-xl font-semibold text-center mb-4">
              Create a New Memory
            </h2>

            <MediaUpload onMediaSelect={(file) => setMediaFile(file)} />

            {mediaFile && (
              <div className="mt-4 mb-6 text-center">
                <h3 className="text-sm font-medium text-gray-700 mb-2">
                  Preview
                </h3>
                {mediaFile.type.startsWith("video") ? (
                  <video
                    src={URL.createObjectURL(mediaFile)}
                    controls
                    className="w-48 h-auto mx-auto rounded"
                  />
                ) : (
                  <img
                    src={URL.createObjectURL(mediaFile)}
                    alt="Uploaded"
                    className="w-48 h-auto mx-auto rounded"
                  />
                )}
              </div>
            )}

            <VoiceRecorder onAudioCapture={(blob) => setAudioBlob(blob)} />

            <div className="text-center mt-6">
              <button
                onClick={handleMemorySubmit}
                className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700"
                disabled={loading}
              >
                {loading ? "Processing..." : "Transform Memory"}
              </button>
            </div>

            <button
              className="absolute top-4 right-4 text-gray-500 hover:text-gray-700 text-2xl"
              onClick={() => setShowModal(false)}
            >
              &times;
            </button>
          </div>
        </div>
      )}
    </>
  );
}

export default App;
