import React, { useCallback, useEffect, useRef, useState } from "react";
import { useImageMixer } from "./ImageMixerContext";

export function ImageViewer({ index }) {
  const {
    images,
    uploadImage,
    adjustBrightnessContrast,
    cancelBrightnessAdjustments,
    resetBrightnessContrast,
    getImageComponent,
    componentTypes,
  } = useImageMixer();
  const fileInputRef = useRef(null);
  const dragRef = useRef(null);
  const pendingToneRef = useRef(null);
  const toneTimerRef = useRef(null);

  const [brightness, setBrightness] = useState(0);
  const [contrast, setContrast] = useState(0);

  const openBrowse = () => fileInputRef.current?.click();

  const onFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    await uploadImage(file, index);
  };

  const flushToneUpdate = useCallback((includeImage = false) => {
    if (!pendingToneRef.current) {
      return;
    }

    const { nextBrightness, nextContrast } = pendingToneRef.current;
    pendingToneRef.current = null;

    adjustBrightnessContrast(index, nextBrightness, nextContrast, {
      includeImage,
      abortPrevious: true,
    }).catch(() => {});
  }, [adjustBrightnessContrast, index]);

  const scheduleToneUpdate = useCallback((nextBrightness, nextContrast) => {
    pendingToneRef.current = { nextBrightness, nextContrast };

    if (toneTimerRef.current) {
      return;
    }

    toneTimerRef.current = setTimeout(() => {
      toneTimerRef.current = null;
      flushToneUpdate(false);
    }, 45);
  }, [flushToneUpdate]);

  const onMouseMove = useCallback((event) => {
    const dragState = dragRef.current;
    if (!dragState) {
      return;
    }

    const dx = event.clientX - dragState.x;
    const dy = dragState.y - event.clientY;

    // Requested interaction: vertical drag controls contrast, horizontal controls brightness.
    const nextBrightness = Math.max(-255, Math.min(255, dragState.b + dx));
    const nextContrast = Math.max(-0.9, Math.min(3.0, dragState.c + dy / 160));

    setBrightness(nextBrightness);
    setContrast(nextContrast);
    scheduleToneUpdate(nextBrightness, nextContrast);
  }, [scheduleToneUpdate]);

  const stopDragging = useCallback(() => {
    if (!dragRef.current) {
      return;
    }

    dragRef.current = null;
    window.removeEventListener("mousemove", onMouseMove);
    window.removeEventListener("mouseup", stopDragging);

    if (toneTimerRef.current) {
      clearTimeout(toneTimerRef.current);
      toneTimerRef.current = null;
    }

    flushToneUpdate(false);
    getImageComponent(index, componentTypes[index]).catch(() => {});
  }, [componentTypes, flushToneUpdate, getImageComponent, index, onMouseMove]);

  const onMouseDown = (event) => {
    if (event.button !== 0 || !images[index]) {
      return;
    }

    dragRef.current = { x: event.clientX, y: event.clientY, b: brightness, c: contrast };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", stopDragging);
  };

  useEffect(() => {
    return () => {
      if (toneTimerRef.current) {
        clearTimeout(toneTimerRef.current);
      }
      cancelBrightnessAdjustments(index);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", stopDragging);
    };
  }, [cancelBrightnessAdjustments, index, onMouseMove, stopDragging]);

  const brightnessCss = Math.max(0.25, 1 + brightness / 255);
  const contrastCss = Math.max(0.1, 1 + contrast);

  return (
    <div className="viewer-card" onDoubleClick={openBrowse}>
      <div className="viewer-header row-between">
        <span>Input Image {index + 1}</span>
        <button type="button" onClick={openBrowse}>Browse</button>
      </div>
      <div className="viewer-body" onMouseDown={onMouseDown}>
        {images[index] ? (
          <img
            src={`data:image/png;base64,${images[index]}`}
            alt={`Input ${index + 1}`}
            className="fit-image"
            style={{ filter: `brightness(${brightnessCss}) contrast(${contrastCss})` }}
          />
        ) : (
          <div className="placeholder">Double-click to load image</div>
        )}
      </div>
      <div className="viewer-footer">
        <small>B {brightness.toFixed(0)} / C {contrast.toFixed(2)}</small>
        <button
          type="button"
          onClick={async () => {
            if (toneTimerRef.current) {
              clearTimeout(toneTimerRef.current);
              toneTimerRef.current = null;
            }
            pendingToneRef.current = null;
            cancelBrightnessAdjustments(index);
            setBrightness(0);
            setContrast(0);
            await resetBrightnessContrast(index);
            await getImageComponent(index, componentTypes[index]);
          }}
        >
          Reset
        </button>
      </div>
      <input ref={fileInputRef} type="file" accept="image/*" style={{ display: "none" }} onChange={onFile} />
    </div>
  );
}
