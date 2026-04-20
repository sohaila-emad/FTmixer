import React, { useRef } from "react";
import { useTransformExplorer } from "./TransformExplorerContext";

export function TransformControlPanel() {
  const {
    operations,
    selectedOperation,
    selectedOperationId,
    setSelectedOperationId,
    parameterValues,
    setParamValue,
    repeatFourierCount,
    setRepeatFourierCount,
    domain,
    setDomain,
    isApplying,
    progress,
    error,
    hasSource,
    uploadSource,
    applyOperation,
  } = useTransformExplorer();

  const fileRef = useRef(null);
  const currentWindowType = String(parameterValues.window_type || "rectangular");

  const visibleFields = (selectedOperation?.parameters || []).filter((field) => {
    if (!Array.isArray(field.windowTypes)) {
      return true;
    }
    return field.windowTypes.includes(currentWindowType);
  });

  const renderField = (field) => {
    const value = parameterValues[field.id];

    if (field.type === "select") {
      return (
        <select value={String(value)} onChange={(event) => setParamValue(field.id, event.target.value)}>
          {(field.options || []).map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      );
    }

    if (field.type === "bool") {
      return (
        <label className="inline-toggle">
          <input
            type="checkbox"
            checked={Boolean(value)}
            onChange={(event) => setParamValue(field.id, event.target.checked)}
          />
          <span>{Boolean(value) ? "Enabled" : "Disabled"}</span>
        </label>
      );
    }

    const isInt = field.type === "int";
    return (
      <input
        type="number"
        value={value}
        min={field.min}
        max={field.max}
        step={field.step}
        onChange={(event) => {
          const raw = event.target.value;
          if (raw === "") {
            setParamValue(field.id, "");
            return;
          }
          setParamValue(field.id, isInt ? Number.parseInt(raw, 10) : Number.parseFloat(raw));
        }}
      />
    );
  };

  return (
    <div className="panel-stack">
      <div className="panel-card">
        <h3>Source Image</h3>
        <button type="button" onClick={() => fileRef.current?.click()} disabled={isApplying}>
          Upload Source Image
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          onChange={async (event) => {
            const file = event.target.files?.[0];
            if (!file) {
              return;
            }
            await uploadSource(file);
            event.target.value = "";
          }}
        />
        <p className="muted">{hasSource ? "Source loaded" : "No source loaded yet"}</p>
      </div>

      <div className="panel-card">
        <h3>Operation</h3>
        <select value={selectedOperationId} onChange={(event) => setSelectedOperationId(event.target.value)}>
          {operations.map((operation) => (
            <option key={operation.id} value={operation.id}>
              {operation.name}
            </option>
          ))}
        </select>
        <p className="muted">{selectedOperation?.description || ""}</p>
      </div>

      <div className="panel-card">
        <h3>Apply Domain</h3>
        <select value={domain} onChange={(event) => setDomain(event.target.value)}>
          <option value="spatial">Spatial Domain</option>
          <option value="frequency">Frequency Domain</option>
        </select>
      </div>

      <div className="panel-card">
        <h3>Repeated Fourier (Global)</h3>
        <label>
          <span>Count</span>
          <input
            type="number"
            value={repeatFourierCount}
            min={0}
            max={12}
            step={1}
            onChange={(event) => {
              const raw = event.target.value;
              if (raw === "") {
                setRepeatFourierCount(0);
                return;
              }
              const parsed = Number.parseInt(raw, 10);
              const safe = Number.isNaN(parsed) ? 0 : Math.max(0, Math.min(12, parsed));
              setRepeatFourierCount(safe);
            }}
          />
        </label>
        <p className="muted">Applied after the selected operation, in whichever domain you chose.</p>
      </div>

      <div className="panel-card">
        <h3>Parameters</h3>
        {visibleFields.length ? (
          <div className="param-grid">
            {visibleFields.map((field) => (
              <label key={field.id}>
                <span>{field.label}</span>
                {renderField(field)}
              </label>
            ))}
          </div>
        ) : (
          <p className="muted">No parameters</p>
        )}
      </div>

      <div className="panel-card">
        <button type="button" onClick={() => applyOperation()} disabled={!hasSource}>
          {isApplying ? "Applying..." : "Apply Operation"}
        </button>
        <div className="progress-wrap" style={{ marginTop: "0.5rem" }}>
          <div className="progress-bar" style={{ width: `${progress}%` }} />
        </div>
        <p className="muted">{isApplying ? `Processing ${progress}%` : "Ready"}</p>
        {error ? <p className="error-text">{error}</p> : null}
      </div>
    </div>
  );
}
