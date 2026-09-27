import React from "react";

// Full class strings so Tailwind keeps them in the build.
const STYLES = {
  Joy: "bg-amber-400/15 text-amber-300 ring-amber-400/30",
  Love: "bg-rose-400/15 text-rose-300 ring-rose-400/30",
  Gratitude: "bg-emerald-400/15 text-emerald-300 ring-emerald-400/30",
  Hope: "bg-sky-400/15 text-sky-300 ring-sky-400/30",
  Contentment: "bg-teal-400/15 text-teal-300 ring-teal-400/30",
  Surprise: "bg-violet-400/15 text-violet-300 ring-violet-400/30",
  Curiosity: "bg-indigo-400/15 text-indigo-300 ring-indigo-400/30",
  Anger: "bg-red-400/15 text-red-300 ring-red-400/30",
};

const EmotionChip = ({ emotion }) => (
  <span
    className={`rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset ${
      STYLES[emotion] || "bg-gray-400/15 text-gray-300 ring-gray-400/30"
    }`}
  >
    {emotion}
  </span>
);

export default EmotionChip;
