import React, { useState, useRef } from "react";

const VoiceRecorder = ({ onAudioCapture }) => {
  const [recording, setRecording] = useState(false);
  const [audioURL, setAudioURL] = useState(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorderRef.current = new MediaRecorder(stream);

    mediaRecorderRef.current.ondataavailable = (e) => {
      chunksRef.current.push(e.data);
    };

    mediaRecorderRef.current.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      const url = URL.createObjectURL(blob);
      setAudioURL(url);
      onAudioCapture(blob);
      chunksRef.current = [];
    };

    mediaRecorderRef.current.start();
    setRecording(true);
  };

  const stopRecording = () => {
    mediaRecorderRef.current.stop();
    setRecording(false);
  };

  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Record Voice (optional)
      </label>
      {!recording ? (
        <button
          onClick={startRecording}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Start Recording
        </button>
      ) : (
        <button
          onClick={stopRecording}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Stop Recording
        </button>
      )}

      {audioURL && (
        <div className="mt-2">
          <audio controls src={audioURL} />
        </div>
      )}
    </div>
  );
};

export default VoiceRecorder;
