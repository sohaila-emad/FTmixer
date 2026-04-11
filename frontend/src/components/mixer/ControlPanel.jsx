import React, { useRef } from "react";
import { useImageMixer } from "./ImageMixerContext";
import { MixerProgressBar } from "./MixerProgressBar";

export function ControlPanel() {
  const {
    uploadMultipleImages,
    weights,
    setWeights,
    imageModes,
    setImageModes,
    mixingMode,
    setMixingMode,
    regionMode,
    setRegionMode,
    imageRegionModes,
    setImageRegionModes,
    roi,
    setRoi,
    currentOutputViewer,
    setCurrentOutputViewer,
    sizePolicy,
    keepAspectRatio,
    fixedSize,
    setFixedSize,
    applyImageSizing,
    simulateBottleneck,
    setSimulateBottleneck,
    bottleneckSeconds,
    setBottleneckSeconds,
    mixImages,
    isMixing,
  } = useImageMixer();

  const multiInputRef = useRef(null);

  const setWeight = (index, value) => {
    const next = [...weights];
    next[index] = Number(value);
    setWeights(next);
  };

  const setImageMode = (index, value) => {
    const next = [...imageModes];
    next[index] = value;
    setImageModes(next);
  };

  const setImageRegionMode = (index, value) => {
    const next = [...imageRegionModes];
    next[index] = value;
    setImageRegionModes(next);
  };

  const setRoiPart = (idx, value) => {
    const next = [...roi];
    next[idx] = Number(value);
    setRoi(next);
  };

  const componentModeOptions =
    mixingMode === "MAGNITUDE_PHASE"
      ? [
          { value: "MAGNITUDE", label: "Magnitude" },
          { value: "PHASE", label: "Phase" },
        ]
      : [
          { value: "REAL", label: "Real" },
          { value: "IMAGINARY", label: "Imaginary" },
        ];

  return (
    <div className="panel-stack">
      <div className="panel-card">
        <h3>Input</h3>
        <button type="button" onClick={() => multiInputRef.current?.click()} disabled={isMixing}>
          Upload up to 4 images
        </button>
        <input
          ref={multiInputRef}
          type="file"
          multiple
          accept="image/*"
          style={{ display: "none" }}
          onChange={(e) => uploadMultipleImages(e.target.files || [])}
        />
      </div>

      <div className="panel-card">
        <h3>Image Sizing</h3>
        <label>Sizing Policy</label>
        <select
          value={sizePolicy}
          onChange={(e) => {
            const policy = e.target.value;
            applyImageSizing({ policy }).catch(() => {});
          }}
        >
          <option value="smallest">Smallest</option>
          <option value="largest">Largest</option>
          <option value="fixed">Fixed</option>
        </select>

        <label className="inline-toggle" style={{ marginTop: "0.55rem" }}>
          <input
            type="checkbox"
            checked={keepAspectRatio}
            onChange={(e) => {
              const checked = e.target.checked;
              applyImageSizing({ keepAspectRatio: checked, applyNow: false }).catch(() => {});
            }}
          />
          <span>Keep Aspect Ratio</span>
        </label>

        {sizePolicy === "fixed" ? (
          <div className="grid-two" style={{ marginTop: "0.5rem" }}>
            <label>
              Width (px)
              <input
                type="number"
                min={1}
                value={fixedSize.width}
                onChange={(e) => {
                  const width = Number(e.target.value || 1);
                  const next = { ...fixedSize, width };
                  setFixedSize(next);
                  applyImageSizing({ policy: "fixed", fixedWidth: width, fixedHeight: next.height }).catch(() => {});
                }}
              />
            </label>
            <label>
              Height (px)
              <input
                type="number"
                min={1}
                value={fixedSize.height}
                onChange={(e) => {
                  const height = Number(e.target.value || 1);
                  const next = { ...fixedSize, height };
                  setFixedSize(next);
                  applyImageSizing({ policy: "fixed", fixedWidth: next.width, fixedHeight: height }).catch(() => {});
                }}
              />
            </label>
          </div>
        ) : null}
      </div>

      <div className="panel-card">
        <h3>Mixing Mode</h3>
        <select value={mixingMode} onChange={(e) => setMixingMode(e.target.value)}>
          <option value="MAGNITUDE_PHASE">Magnitude / Phase</option>
          <option value="REAL_IMAGINARY">Real / Imaginary</option>
        </select>

        <h3>Region Mode</h3>
        <select value={regionMode} onChange={(e) => setRegionMode(e.target.value)}>
          <option value="FULL">Full</option>
          <option value="INNER_OUTER">Inner / Outer</option>
        </select>

        <h3>Output Port</h3>
        <select value={currentOutputViewer} onChange={(e) => setCurrentOutputViewer(Number(e.target.value))}>
          <option value={0}>Output 1</option>
          <option value={1}>Output 2</option>
        </select>
      </div>

      <div className="panel-card">
        <h3>ROI</h3>
        <div className="grid-two">
          <label>Left <input type="number" value={roi[0]} onChange={(e) => setRoiPart(0, e.target.value)} /></label>
          <label>Top <input type="number" value={roi[1]} onChange={(e) => setRoiPart(1, e.target.value)} /></label>
          <label>Right <input type="number" value={roi[2]} onChange={(e) => setRoiPart(2, e.target.value)} /></label>
          <label>Bottom <input type="number" value={roi[3]} onChange={(e) => setRoiPart(3, e.target.value)} /></label>
        </div>
      </div>

      {weights.map((weight, idx) => (
        <div className="panel-card" key={`weight-${idx}`}>
          <h3>Image {idx + 1}</h3>
          <label>Weight: {weight}%</label>
          <input type="range" min={0} max={100} value={weight} onChange={(e) => setWeight(idx, e.target.value)} />
          <label>Component Mode</label>
          <select value={imageModes[idx]} onChange={(e) => setImageMode(idx, e.target.value)}>
            {componentModeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <label>Region Mode</label>
          <select value={imageRegionModes[idx]} onChange={(e) => setImageRegionMode(idx, e.target.value)}>
            <option value="INNER">Inner</option>
            <option value="OUTER">Outer</option>
          </select>
        </div>
      ))}

      <div className="panel-card">
        <h3>Processing</h3>
        <label className="inline-toggle">
          <input
            type="checkbox"
            checked={simulateBottleneck}
            onChange={(e) => setSimulateBottleneck(e.target.checked)}
          />
          <span>Simulate FFT Bottleneck</span>
        </label>
        <label>
          Delay Seconds
          <input
            type="number"
            min={0}
            max={10}
            step={0.1}
            value={bottleneckSeconds}
            onChange={(e) => setBottleneckSeconds(Number(e.target.value || 0))}
          />
        </label>
      </div>

      <div className="panel-card">
        <button type="button" onClick={() => mixImages()}>
          {isMixing ? "Remix (Cancel Current)" : "Start Mix"}
        </button>
      </div>

      <MixerProgressBar />
    </div>
  );
}
