import React, { useCallback, useEffect, useRef, useState } from "react";

const formatTime = (seconds) =>
  `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;

// Records one clip. Reports the Blob (or null when discarded) via onAudioCapture.
const VoiceRecorder = ({ onAudioCapture, disabled }) => {
  const [status, setStatus] = useState("idle"); // idle | recording | recorded
  const [seconds, setSeconds] = useState(0);
  const [audioURL, setAudioURL] = useState(null);
  const [error, setError] = useState(null);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  const releaseMic = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    clearInterval(timerRef.current);
  }, []);

  // Release the mic and preview URL if the window closes mid-recording.
  useEffect(() => releaseMic, [releaseMic]);
  useEffect(() => () => audioURL && URL.revokeObjectURL(audioURL), [audioURL]);

  const start = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
      recorder.onstop = () => {
        releaseMic();
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        setAudioURL(URL.createObjectURL(blob));
        setStatus("recorded");
        onAudioCapture(blob);
      };

      recorder.start();
      setSeconds(0);
      setStatus("recording");
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch (e) {
      releaseMic();
      setError(
        e.name === "NotAllowedError"
          ? "Microphone access was blocked. Allow it in your browser's site settings and try again."
          : `Couldn't start recording: ${e.message}`
      );
    }
  };

  const stop = () => recorderRef.current?.stop();

  const discard = () => {
    setAudioURL(null);
    setSeconds(0);
    setStatus("idle");
    onAudioCapture(null);
  };

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
      {status === "idle" && (
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={start}
            disabled={disabled}
            aria-label="Start recording"
            className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-rose-500 text-white shadow-lg shadow-rose-500/20 transition hover:bg-rose-400 disabled:opacity-40"
          >
            <svg className="h-6 w-6" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 14a3 3 0 003-3V5a3 3 0 10-6 0v6a3 3 0 003 3zm5-3a5 5 0 01-10 0H5a7 7 0 006 6.92V21h2v-3.08A7 7 0 0019 11h-2z" />
            </svg>
          </button>
          <div>
            <p className="font-medium text-white">Tap to start recording</p>
            <p className="text-sm text-gray-400">Tell the memory in your own words: who, where, what happened.</p>
          </div>
        </div>
      )}

      {status === "recording" && (
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={stop}
            aria-label="Stop recording"
            className="relative flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-rose-500 text-white"
          >
            <span className="absolute inset-0 animate-ping rounded-full bg-rose-500/40" />
            <span className="relative h-5 w-5 rounded-sm bg-white" />
          </button>
          <div>
            <p className="flex items-center gap-2 font-medium text-white">
              <span className="h-2 w-2 animate-pulse rounded-full bg-rose-400" />
              Recording <span className="font-mono text-rose-300">{formatTime(seconds)}</span>
            </p>
            <p className="text-sm text-gray-400">Tap the square when you're done.</p>
          </div>
        </div>
      )}

      {status === "recorded" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="flex items-center gap-2 font-medium text-white">
              <svg className="h-5 w-5 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 111.4-1.4L8 12.58l7.3-7.3a1 1 0 011.4 0z"
                  clipRule="evenodd"
                />
              </svg>
              Recording ready <span className="font-mono text-sm text-gray-400">{formatTime(seconds)}</span>
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  discard();
                  start();
                }}
                disabled={disabled}
                className="rounded-lg px-3 py-1.5 text-sm text-gray-300 transition hover:bg-white/10 disabled:opacity-40"
              >
                Re-record
              </button>
              <button
                type="button"
                onClick={discard}
                disabled={disabled}
                className="rounded-lg px-3 py-1.5 text-sm text-gray-400 transition hover:bg-white/10 hover:text-rose-300 disabled:opacity-40"
              >
                Discard
              </button>
            </div>
          </div>
          <audio controls src={audioURL} className="w-full" style={{ colorScheme: "dark" }} />
        </div>
      )}

      {error && <p className="mt-3 text-sm text-rose-300">{error}</p>}
    </div>
  );
};

export default VoiceRecorder;
