import React, { useRef } from "react";

const MemoryDisplay = ({ memory }) => {
  const audioRef = useRef(null);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white p-8 rounded-xl shadow-md">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">
              Your Memory Story
            </h2>
            <div className="prose prose-lg">
              <p className="text-gray-700 leading-relaxed">{memory.story}</p>
            </div>

            <div className="mt-8">
              <h3 className="text-xl font-medium text-gray-800 mb-3">
                Listen to Your Memory
              </h3>
              <audio
                ref={audioRef}
                src={memory.audioUrl}
                controls
                className="w-full"
              >
                Your browser does not support the audio element.
              </audio>
            </div>
          </div>

          <div>
            <h3 className="text-xl font-medium text-gray-800 mb-3">
              Memory Visualization
            </h3>
            <div className="relative rounded-lg overflow-hidden shadow-lg">
              <img
                src={memory.imageUrl}
                alt="Generated memory visualization"
                className="w-full h-auto"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MemoryDisplay;
