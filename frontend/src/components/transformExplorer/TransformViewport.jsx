import React from "react";
import { useTransformExplorer } from "./TransformExplorerContext";

const COMPONENT_OPTIONS = ["magnitude", "phase", "real", "imaginary"];

export function TransformViewport({ viewportKey, title }) {
  const { viewports, componentSelections, setViewportComponent } = useTransformExplorer();

  const componentName = componentSelections[viewportKey] || "magnitude";
  const viewportData = viewports[viewportKey];
  const imageData = viewportData?.[componentName] || null;

  return (
    <div className="viewer-card">
      <div className="viewer-header row-between">
        <span>{title}</span>
        <select value={componentName} onChange={(event) => setViewportComponent(viewportKey, event.target.value)}>
          {COMPONENT_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option.charAt(0).toUpperCase() + option.slice(1)}
            </option>
          ))}
        </select>
      </div>
      <div className="viewer-body">
        {imageData ? (
          <img src={`data:image/png;base64,${imageData}`} alt={`${title} ${componentName}`} className="fit-image" />
        ) : (
          <div className="placeholder">No data yet</div>
        )}
      </div>
    </div>
  );
}
