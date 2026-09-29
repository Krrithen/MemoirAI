import React, { useState } from "react";
import CreateMemory from "./components/CreateMemory";
import MemoriesGallery from "./components/MemoriesGallery";
import MemoryDetail from "./components/MemoryDetail";
import memoirLogo from "./MemoirAI.png";
import "./index.css";

function App() {
  const [creating, setCreating] = useState(false);
  const [selectedMemory, setSelectedMemory] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // The memory comes back 'pending'; the gallery shows its progress until it's ready.
  const handleCreated = () => {
    setCreating(false);
    setRefreshKey((k) => k + 1);
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
            </div>
          </div>
        </div>

        {/* Right Section (Scrollable) */}
        <div className="w-3/4 h-screen overflow-y-auto p-4 bg-[#0a0f1c] shadow-xl">
          <div className="max-w-7xl mx-auto flex-grow">
            <MemoriesGallery refreshKey={refreshKey} onSelect={setSelectedMemory} />
          </div>
        </div>
      </div>

      {/* Floating Create Memory Button */}
      <button
        onClick={() => setCreating(true)}
        className="fixed bottom-6 right-6 bg-blue-500 text-white px-5 py-3 rounded-full shadow-lg hover:bg-blue-700 transition z-40"
      >
        + Create Memory
      </button>

      {creating && <CreateMemory onClose={() => setCreating(false)} onCreated={handleCreated} />}
      {selectedMemory && <MemoryDetail memory={selectedMemory} onClose={() => setSelectedMemory(null)} />}
    </>
  );
}

export default App;
