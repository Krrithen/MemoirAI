import React, { useState } from "react";
import MediaUpload from "./MediaUpload";
import VoiceRecorder from "./VoiceRecorder";

const MemoryInput = ({ onSubmit, isLoading }) => {
  const [textMemory, setTextMemory] = useState("");
  const [recordedAudioBlob, setRecordedAudioBlob] = useState(null);
  const [mediaFile, setMediaFile] = useState(null); // <- for image/video

  const handleSubmit = (e) => {
    e.preventDefault();

    const memoryData = {
      text: textMemory,
      audioBlob: recordedAudioBlob || null,
      mediaFile: mediaFile || null, // Include image/video file
    };

    onSubmit(memoryData);
  };

  return (
    <div className="max-w-2xl mx-auto bg-white p-8 rounded-xl shadow-md">
      <form onSubmit={handleSubmit}>
        <div className="mb-6">
          <label
            htmlFor="memory-text"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Describe your memory
          </label>
          <textarea
            id="memory-text"
            placeholder="Tell us about a moment you'd like to transform..."
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-primary"
            rows="4"
            value={textMemory}
            onChange={(e) => setTextMemory(e.target.value)}
            required
          />
        </div>

        {/* Upload image or video */}
        <MediaUpload onMediaSelect={(file) => setMediaFile(file)} />

        {/* Voice recording */}
        <VoiceRecorder onAudioCapture={(blob) => setRecordedAudioBlob(blob)} />

        <div className="text-center">
          <button
            type="submit"
            className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-opacity-90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={
              isLoading || (!textMemory && !recordedAudioBlob && !mediaFile)
            }
          >
            {isLoading ? (
              <span className="flex items-center justify-center">
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Processing...
              </span>
            ) : (
              "Transform Memory"
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default MemoryInput;
