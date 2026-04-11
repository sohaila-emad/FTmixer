import React from "react";
import { useTransformExplorer } from "./TransformExplorerContext";

const FALLBACK_GUIDE = {
  summary:
    "Change one parameter at a time, apply, then compare Spatial Transformed and Frequency Transformed to understand cause and effect.",
  expected: [
    "Spatial apply: operation is applied on spatial data first, then FFT is recomputed.",
    "Frequency apply: operation is applied on frequency data first, then spatial is reconstructed with IFFT.",
  ],
};

const OP_GUIDES = {
  shift: {
    summary: "Circular shift with wrap-around boundaries.",
    expected: [
      "In spatial: content wraps across borders as x/y offsets increase.",
      "In frequency: phase pattern changes consistently with the same shift operation.",
    ],
  },
  complex_exponential: {
    summary: "Multiplies data by A * exp(j * (wx*x + wy*y + phase)).",
    expected: [
      "Amplitude A scales magnitude.",
      "wx and wy create linear phase ramps.",
      "phase adds a global phase offset.",
    ],
  },
  stretch: {
    summary: "Center-referenced scaling on a fixed canvas.",
    expected: [
      "Window size stays fixed while content is scaled around center.",
      "Scale X > 1 stretches horizontally; Scale Y > 1 stretches vertically.",
    ],
  },
  window_multiply: {
    summary: "Sliding-kernel style filtering using selected window kernel.",
    expected: [
      "Rectangular: averaging-style blur by kernel size.",
      "Gaussian: smooth blur controlled by sigma_x/sigma_y.",
      "Hanning/Hamming: weighted smoothing with window-specific behavior.",
    ],
  },
};

function estimateShiftBins(omega, size) {
  if (!size) {
    return "n/a";
  }
  const bins = (omega * size) / (2 * Math.PI);
  return `${bins.toFixed(2)} bins`;
}

function estimatePeriod(omega) {
  const absOmega = Math.abs(omega);
  if (absOmega < 1e-9) {
    return "infinite";
  }
  return `${(2 * Math.PI / absOmega).toFixed(2)} px/cycle`;
}

export function TransformGuidePanel() {
  const { selectedOperationId, selectedOperation, domain, parameterValues, sourceShape } = useTransformExplorer();

  const guide = OP_GUIDES[selectedOperationId] || FALLBACK_GUIDE;
  const omegaX = Number(parameterValues.omega_x || 0);
  const omegaY = Number(parameterValues.omega_y || 0);
  const phase = Number(parameterValues.phase || 0);
  const amplitude = Number(parameterValues.amplitude || 1);
  const width = Number(sourceShape?.width || 0);
  const height = Number(sourceShape?.height || 0);

  const isComplexExp = selectedOperationId === "complex_exponential";

  return (
    <section className="guide-shell">
      <div className="guide-header">
        <h2>Operation Guide</h2>
        <span className="guide-domain-chip">Apply Domain: {domain}</span>
      </div>

      <div className="guide-grid">
        <article className="guide-card-right">
          <h3>Current Operation</h3>
          <p className="guide-op-name">{selectedOperation?.name || "No operation selected"}</p>
          <p className="guide-copy">{guide.summary}</p>
          <ul className="guide-list">
            {guide.expected.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </article>

        <article className="guide-card-right">
          <h3>Units</h3>
          <div className="guide-kv">
            <div><strong>Amplitude</strong>: unitless gain</div>
            <div><strong>Omega X/Y</strong>: radians per pixel</div>
            <div><strong>Phase</strong>: radians</div>
          </div>
          <p className="guide-copy">
            Practical reading: if omega gets larger in magnitude, phase changes faster across the image.
          </p>
        </article>
      </div>

      {isComplexExp ? (
        <article className="guide-card-right guide-complex-live">
          <h3>Complex Exponential Live Hints</h3>
          <div className="guide-metrics">
            <div className="guide-metric"><span>A</span><strong>{amplitude.toFixed(2)}</strong></div>
            <div className="guide-metric"><span>wx</span><strong>{omegaX.toFixed(3)}</strong></div>
            <div className="guide-metric"><span>wy</span><strong>{omegaY.toFixed(3)}</strong></div>
            <div className="guide-metric"><span>phase</span><strong>{phase.toFixed(3)}</strong></div>
          </div>
          <div className="guide-grid guide-grid-2">
            <div className="guide-pill">X ramp period: {estimatePeriod(omegaX)}</div>
            <div className="guide-pill">Y ramp period: {estimatePeriod(omegaY)}</div>
            <div className="guide-pill">Estimated X frequency shift: {estimateShiftBins(omegaX, width)}</div>
            <div className="guide-pill">Estimated Y frequency shift: {estimateShiftBins(omegaY, height)}</div>
          </div>
          <p className="guide-copy">
            If transformed magnitude looks similar after small changes, phase view usually shows the effect more clearly.
          </p>
        </article>
      ) : null}
    </section>
  );
}
