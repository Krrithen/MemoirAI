import React, { useEffect, useRef } from "react";

const ElevenLabsConvai = () => {
  const containerRef = useRef(null);

  useEffect(() => {
    const scriptId = "elevenlabs-widget-script";
    const container = containerRef.current;

    if (!document.getElementById(scriptId)) {
      const script = document.createElement("script");
      script.src = "https://elevenlabs.io/convai-widget/index.js";
      script.async = true;
      script.type = "text/javascript";
      script.id = scriptId;

      script.onload = () => {
        if (container && !container.querySelector("elevenlabs-convai")) {
          const widget = document.createElement("elevenlabs-convai");
          widget.setAttribute("agent-id", "RWbsVT7HJXMIoFe1EnU6");
          widget.style.position = "relative";
          widget.style.width = "100%";
          widget.style.height = "100%";
          container.appendChild(widget);
        }
      };

      script.onerror = (error) => {
        console.error("Error loading ElevenLabs widget script:", error);
      };

      document.head.appendChild(script);
    }

    return () => {
      const oldScript = document.getElementById(scriptId);
      if (oldScript) document.head.removeChild(oldScript);
      if (container) container.innerHTML = "";
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="absolute bottom-16 left-0 right-0"
      style={{ height: "200px" }}
    ></div>
  );
};

export default ElevenLabsConvai;
