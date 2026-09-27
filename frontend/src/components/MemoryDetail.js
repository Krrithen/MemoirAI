import React, { useState } from "react";
import EmotionChip from "./EmotionChip";
import Modal from "./Modal";

const formatDate = (iso) =>
  new Date(iso).toLocaleString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

const MemoryDetail = ({ memory, onClose }) => {
  const [view, setView] = useState("story"); // story | transcript
  const hasVisual = Boolean(memory.imageUrl || memory.videoUrl);
  const text = view === "story" ? memory.story : memory.transcript;

  return (
    <Modal onClose={onClose} labelledBy="memory-title" maxWidth={hasVisual ? "max-w-5xl" : "max-w-2xl"}>
      <div className={hasVisual ? "grid md:grid-cols-5" : ""}>
        {hasVisual && (
          <div className="flex items-center justify-center bg-black md:col-span-2 md:rounded-l-2xl">
            {memory.imageUrl ? (
              <img src={memory.imageUrl} alt="" className="max-h-[40vh] w-full object-contain md:max-h-[90vh]" />
            ) : (
              <video
                src={memory.videoUrl}
                controls
                className="max-h-[40vh] w-full object-contain md:max-h-[90vh]"
              />
            )}
          </div>
        )}

        <div className={`space-y-6 p-6 sm:p-8 ${hasVisual ? "md:col-span-3" : ""}`}>
          <header className="space-y-3 pr-10">
            <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
              {memory.timestamp ? formatDate(memory.timestamp) : ""}
            </p>
            <h2 id="memory-title" className="text-2xl font-semibold leading-tight text-white sm:text-3xl">
              {memory.title}
            </h2>
            {memory.tags?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {memory.tags.map((tag) => (
                  <EmotionChip key={tag} emotion={tag} />
                ))}
              </div>
            )}
          </header>

          {memory.audioUrl && (
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500">Original recording</p>
              <audio controls src={memory.audioUrl} className="w-full" style={{ colorScheme: "dark" }} />
            </div>
          )}

          <section className="space-y-3">
            {memory.transcript && (
              <div className="inline-flex rounded-lg bg-white/5 p-1 text-sm" role="tablist">
                {[
                  ["story", "Story"],
                  ["transcript", "What you said"],
                ].map(([key, label]) => (
                  <button
                    key={key}
                    role="tab"
                    aria-selected={view === key}
                    onClick={() => setView(key)}
                    className={`rounded-md px-3 py-1.5 transition ${
                      view === key ? "bg-white/10 text-white" : "text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
            {view === "story" && memory.storyStyle === "creative" && (
              <p className="text-xs text-gray-500">
                Retold by AI from your recording. It may add atmosphere; "What you said" is your exact words.
              </p>
            )}
            <p
              className={`whitespace-pre-line text-[15px] leading-7 ${
                view === "story" ? "text-gray-200" : "font-mono text-sm text-gray-400"
              }`}
            >
              {text}
            </p>
          </section>
        </div>
      </div>
    </Modal>
  );
};

export default MemoryDetail;
