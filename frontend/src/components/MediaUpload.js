import React, { useEffect, useRef, useState } from "react";

// Mirrors the backend limits so oversize files are caught before uploading.
const MAX_BYTES = { image: 5 * 1024 * 1024, video: 50 * 1024 * 1024 };

// Optional photo or video. Reports the File (or null when removed) via onMediaSelect.
const MediaUpload = ({ file, onMediaSelect, disabled }) => {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState(null);
  const [previewURL, setPreviewURL] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!file) {
      setPreviewURL(null);
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setPreviewURL(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const choose = (candidate) => {
    setError(null);
    if (!candidate) return;
    const kind = candidate.type.split("/")[0];
    if (!MAX_BYTES[kind]) {
      return setError("Please choose a photo or a video.");
    }
    if (candidate.size > MAX_BYTES[kind]) {
      return setError(`That ${kind} is too large (max ${MAX_BYTES[kind] / 1024 / 1024} MB).`);
    }
    onMediaSelect(candidate);
  };

  if (file && previewURL) {
    return (
      <div className="relative overflow-hidden rounded-xl border border-white/10 bg-black">
        {file.type.startsWith("video") ? (
          <video src={previewURL} controls className="max-h-56 w-full object-contain" />
        ) : (
          <img src={previewURL} alt="Selected" className="max-h-56 w-full object-contain" />
        )}
        <div className="flex items-center justify-between gap-3 border-t border-white/10 bg-[#111827] px-4 py-2 text-sm">
          <span className="truncate text-gray-300">{file.name}</span>
          <button
            type="button"
            onClick={() => onMediaSelect(null)}
            disabled={disabled}
            className="shrink-0 rounded-lg px-2 py-1 text-gray-400 transition hover:bg-white/10 hover:text-rose-300 disabled:opacity-40"
          >
            Remove
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          choose(e.dataTransfer.files[0]);
        }}
        className={`flex w-full flex-col items-center gap-1 rounded-xl border border-dashed px-4 py-6 text-center transition disabled:opacity-40 ${
          dragging ? "border-sky-400 bg-sky-400/10" : "border-white/15 hover:border-white/30 hover:bg-white/[0.03]"
        }`}
      >
        <svg className="h-7 w-7 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M2.25 15.75l5.16-5.16a2.25 2.25 0 013.18 0l5.16 5.16m-1.5-1.5l1.41-1.41a2.25 2.25 0 013.18 0l2.91 2.91M3.75 21h16.5A1.5 1.5 0 0021.75 19.5V4.5A1.5 1.5 0 0020.25 3H3.75A1.5 1.5 0 002.25 4.5v15A1.5 1.5 0 003.75 21z"
          />
        </svg>
        <span className="text-sm text-gray-300">
          Drop a photo or video here, or <span className="text-sky-300 underline">browse</span>
        </span>
        <span className="text-xs text-gray-500">Photos up to 5 MB, videos up to 50 MB</span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/*,video/*"
        className="hidden"
        onChange={(e) => {
          choose(e.target.files[0]);
          e.target.value = "";
        }}
      />
      {error && <p className="mt-2 text-sm text-rose-300">{error}</p>}
    </div>
  );
};

export default MediaUpload;
