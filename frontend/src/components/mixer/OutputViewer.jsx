import React from "react";
import { useImageMixer } from "./ImageMixerContext";

export function OutputViewer({ index }) {
  const { outputImages } = useImageMixer();

  return (
    <div className="viewer-card">
      <div className="viewer-header">Output {index + 1}</div>
      <div className="viewer-body">
        {outputImages[index] ? (
          <img src={`data:image/png;base64,${outputImages[index]}`} alt={`Output ${index + 1}`} className="fit-image" />
        ) : (
          <div className="placeholder">Mixed result appears here</div>
        )}
      </div>
    </div>
  );
}
