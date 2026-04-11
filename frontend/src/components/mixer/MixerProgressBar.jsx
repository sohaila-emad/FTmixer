import React, { useEffect, useState } from "react";
import { useImageMixer } from "./ImageMixerContext";

export function MixerProgressBar() {
  const { isMixing, mixingProgress } = useImageMixer();
  const [displayProgress, setDisplayProgress] = useState(0);

  useEffect(() => {
    if (!isMixing && mixingProgress === 0) {
      setDisplayProgress(0);
      return;
    }

    const timer = setInterval(() => {
      setDisplayProgress((prev) => {
        if (prev === mixingProgress) {
          return prev;
        }
        if (prev < mixingProgress) {
          return Math.min(mixingProgress, prev + Math.max(1, Math.ceil((mixingProgress - prev) / 10)));
        }
        return Math.max(mixingProgress, prev - 2);
      });
    }, 30);

    return () => clearInterval(timer);
  }, [isMixing, mixingProgress]);

  return (
    <div className="panel-card">
      <h3>Processing</h3>
      <div className="progress-wrap">
        <div className="progress-bar" style={{ width: `${displayProgress}%` }} />
      </div>
      <p className="muted">{isMixing ? `Mixing... ${Math.round(displayProgress)}%` : "Ready"}</p>
    </div>
  );
}
