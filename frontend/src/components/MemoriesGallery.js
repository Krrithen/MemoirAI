import React, { useEffect, useState } from "react";
import { API_URL } from "../config";

// Reloads whenever refreshKey changes (e.g. after a memory is created).
const MemoriesGallery = ({ refreshKey, onSelect }) => {
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMemories = async () => {
      try {
        const response = await fetch(`${API_URL}/api/memories`);
        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }
        const data = await response.json();
        setMemories(data.memories ?? []);
        setError(null);
      } catch (error) {
        console.error("Error fetching memories:", error);
        setError(`Couldn't load memories from ${API_URL} (${error.message}). Is the backend running?`);
      } finally {
        setLoading(false);
      }
    };

    fetchMemories();
  }, [refreshKey]);

  if (loading) {
    return (
      <div className="text-center text-gray-400 p-8">Loading memories...</div>
    );
  }

  if (error) {
    return <div className="text-center text-red-400 p-8">{error}</div>;
  }

  if (memories.length === 0) {
    return (
      <div className="text-center text-gray-400 p-8">
        No memories yet. Use "+ Create Memory" to record your first one.
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        {memories.map((memory) => (
          <div
            key={memory.id}
            onClick={() => onSelect(memory)}
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
    </div>
  );
};

export default MemoriesGallery;
