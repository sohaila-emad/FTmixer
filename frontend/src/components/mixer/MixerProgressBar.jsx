import React from "react";
import { useImageMixer } from "./ImageMixerContext";

export function MixerProgressBar() {
  const { isMixing, mixingProgress } = useImageMixer();

  return (
    <div className="panel-card">
      <h3>Processing</h3>
      <div className="progress-wrap">
        <div className="progress-bar" style={{ width: `${mixingProgress}%` }} />
      </div>
      <p className="muted">{isMixing ? `Mixing... ${mixingProgress}%` : "Ready"}</p>
    </div>
  );
}
