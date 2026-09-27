import React, { useEffect, useState } from "react";
import { API_URL } from "../config";
import MediaUpload from "./MediaUpload";
import Modal from "./Modal";
import VoiceRecorder from "./VoiceRecorder";

const CreateMemory = ({ onClose, onCreated }) => {
  const [audioBlob, setAudioBlob] = useState(null);
  const [mediaFile, setMediaFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!saving) return undefined;
    setElapsed(0);
    const timer = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [saving]);

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("audio", new File([audioBlob], "recording.webm", { type: audioBlob.type || "audio/webm" }));
      if (mediaFile) {
        formData.append(mediaFile.type.startsWith("video") ? "video" : "image", mediaFile);
      }

      const response = await fetch(`${API_URL}/api/memories`, { method: "POST", body: formData });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(body.detail || `The server returned ${response.status}`);
      }
      onCreated(body);
    } catch (e) {
      setError(e.message === "Failed to fetch" ? `Couldn't reach the backend at ${API_URL}.` : e.message);
      setSaving(false);
    }
  };

  return (
    <Modal onClose={onClose} labelledBy="create-memory-title" locked={saving}>
      <div className="space-y-6 p-6 sm:p-8">
        <header>
          <h2 id="create-memory-title" className="text-2xl font-semibold text-white">
            New memory
          </h2>
          <p className="mt-1 text-sm text-gray-400">
            Record it in your own words. It's transcribed and turned into a story on this machine, and your original
            words are always kept.
          </p>
        </header>

        <section className="space-y-2">
          <h3 className="flex items-baseline gap-2 text-sm font-medium text-gray-200">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/10 text-xs">1</span>
            Your voice
            <span className="text-xs font-normal text-gray-500">required</span>
          </h3>
          <VoiceRecorder onAudioCapture={setAudioBlob} disabled={saving} />
        </section>

        <section className="space-y-2">
          <h3 className="flex items-baseline gap-2 text-sm font-medium text-gray-200">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/10 text-xs">2</span>
            A photo or video
            <span className="text-xs font-normal text-gray-500">optional</span>
          </h3>
          <MediaUpload file={mediaFile} onMediaSelect={setMediaFile} disabled={saving} />
        </section>

        {error && (
          <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">
            <span className="font-medium">Couldn't save this memory.</span> {error}
          </div>
        )}

        <footer className="flex flex-col-reverse items-stretch gap-3 border-t border-white/10 pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-gray-500">
            {saving
              ? `Transcribing and writing your story… ${elapsed}s (usually about 10s)`
              : audioBlob
                ? "Ready when you are."
                : "Record something to continue."}
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="rounded-lg px-4 py-2 text-sm text-gray-300 transition hover:bg-white/10 disabled:opacity-40"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={submit}
              disabled={!audioBlob || saving}
              className="flex min-w-[9rem] items-center justify-center gap-2 rounded-lg bg-sky-500 px-5 py-2 text-sm font-medium text-white shadow-lg shadow-sky-500/20 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-gray-500 disabled:shadow-none"
            >
              {saving && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />}
              {saving ? "Saving…" : "Save memory"}
            </button>
          </div>
        </footer>
      </div>
    </Modal>
  );
};

export default CreateMemory;
