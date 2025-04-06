import React, { useEffect, useState, useRef } from "react";

const MemoriesGallery = () => {
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMemory, setSelectedMemory] = useState(null);
  const audioRef = useRef(null);

  useEffect(() => {
    const fetchMemories = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/memories");
        const data = await response.json();
        setMemories(data.memories);
      } catch (error) {
        console.error("Error fetching memories:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchMemories();
  }, []);

  // Auto-play audio when a memory is selected
  useEffect(() => {
    if (selectedMemory && selectedMemory.audioUrl && audioRef.current) {
      audioRef.current.play().catch((e) => {
        console.warn("Audio autoplay failed:", e);
      });
    }
  }, [selectedMemory]);

  if (loading) {
    return (
      <div className="text-center text-gray-400 p-8">Loading memories...</div>
    );
  }

  return (
    <div className="w-full">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        {memories.map((memory) => (
          <div
            key={memory.id}
            onClick={() => setSelectedMemory(memory)}
            className="cursor-pointer relative rounded-lg overflow-hidden shadow-md hover:shadow-xl transition-shadow duration-300 group"
            style={{ aspectRatio: "2/3" }}
          >
            {memory.imageUrl ? (
              <img
                src={memory.imageUrl}
                alt={memory.title}
                className="w-full h-full object-cover"
              />
            ) : memory.videoUrl ? (
              <video
                src={memory.videoUrl}
                className="w-full h-full object-cover"
                muted
                loop
                autoPlay
              />
            ) : (
              <div className="w-full h-full bg-gray-300 flex items-center justify-center text-gray-600">
                No media
              </div>
            )}

            {/* Hover Overlay */}
            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center text-center px-4">
              <div>
                <h3 className="text-white text-lg font-semibold mb-2">
                  {memory.title}
                </h3>
                {/* <p className="text-white text-sm">{memory.story}</p> */}
              </div>
            </div>

            {/* Play Icon for videos */}
            {memory.videoUrl && (
              <div className="absolute top-2 left-2 bg-black bg-opacity-60 rounded-full p-1">
                <svg
                  className="w-6 h-6 text-white"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Modal */}
      {selectedMemory && (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4">
          <div className="bg-white w-full max-w-6xl h-[60vh] rounded-xl overflow-hidden flex relative">
            {/* Close Button */}
            <button
              onClick={() => setSelectedMemory(null)}
              className="absolute top-4 right-4 text-gray-500 hover:text-gray-700 text-2xl z-10"
            >
              &times;
            </button>

            {/* Left Side - Media */}
            <div className="w-1/2 bg-black flex flex-col items-center justify-center p-4">
              {selectedMemory.imageUrl ? (
                <img
                  src={selectedMemory.imageUrl}
                  alt={selectedMemory.title}
                  className="max-h-[75%] object-contain rounded"
                />
              ) : selectedMemory.videoUrl ? (
                <video
                  src={selectedMemory.videoUrl}
                  className="max-h-[75%] object-contain rounded"
                  controls
                  autoPlay
                  muted
                  loop
                />
              ) : (
                <div className="text-white">No media available</div>
              )}

              {selectedMemory.audioUrl && (
                <div className="mt-4 w-full px-2">
                  <audio ref={audioRef} controls className="w-full">
                    <source src={selectedMemory.audioUrl} type="audio/wav" />
                    Your browser does not support the audio element.
                  </audio>
                </div>
              )}
            </div>

            {/* Right Side - Details */}
            <div className="w-1/2 p-6 flex flex-col overflow-y-auto">
              <h2 className="text-2xl font-bold mb-2 text-gray-800">
                {selectedMemory.title}
              </h2>
              <p className="text-gray-600 mb-4">{selectedMemory.story}</p>
              <div className="text-sm text-gray-500 mb-4">
                {new Date(selectedMemory.timestamp).toLocaleString()}
              </div>

              <div className="mt-2">
                <h4 className="text-sm font-semibold text-gray-700 mb-1">
                  Tags:
                </h4>
                <div className="flex flex-wrap gap-2">
                  {selectedMemory.tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className="bg-blue-100 text-blue-700 px-2 py-1 rounded-full text-xs"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>

              {selectedMemory.isComicAvailable && selectedMemory.comicUrl && (
                <div className="mt-4">
                  <a
                    href={selectedMemory.comicUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 underline text-sm"
                  >
                    View Comic Version
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MemoriesGallery;
