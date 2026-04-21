import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useImageMixer } from "./ImageMixerContext";

const MIN_ROI_SPAN = 8;

function clampBoundaries(bounds, width, height) {
  const maxX = Math.max(1, width - 1);
  const maxY = Math.max(1, height - 1);

  let [left, top, right, bottom] = bounds.map((value) => Number(value) || 0);
  left = Math.max(0, Math.min(Math.round(left), maxX));
  top = Math.max(0, Math.min(Math.round(top), maxY));
  right = Math.max(left + 1, Math.min(Math.round(right), maxX));
  bottom = Math.max(top + 1, Math.min(Math.round(bottom), maxY));

  return [left, top, right, bottom];
}

function sameBoundaries(a, b) {
  return a.length === b.length && a.every((value, idx) => value === b[idx]);
}

export function ComponentViewer({ index }) {
  const {
    images,
    components,
    componentTypes,
    setComponentTypes,
    getImageComponent,
    roi,
    setRoi,
    regionMode,
    imageRegionModes,
    adjustBrightnessContrast,
  } = useImageMixer();

  const componentType = componentTypes[index];
  const activeRegionType = regionMode === "INNER_OUTER" ? imageRegionModes[index] : null;
  const bodyRef = useRef(null);
  const imageRef = useRef(null);
  const roiDragRef = useRef(null);
  const toneDragRef = useRef(null);
  const toneUpdateRef = useRef(null);
  const toneRequestCounterRef = useRef(0);

  const [imageFrame, setImageFrame] = useState(null);
  const [tone, setTone] = useState({ brightness: 0, contrast: 0 });

  useEffect(() => {
    if (!images[index]) {
      return;
    }
    getImageComponent(index, componentType).catch(() => {});
  }, [componentType, getImageComponent, images, index]);

  const refreshImageFrame = useCallback(() => {
    if (!imageRef.current || !bodyRef.current) {
      return;
    }

    const imgRect = imageRef.current.getBoundingClientRect();
    const bodyRect = bodyRef.current.getBoundingClientRect();

    setImageFrame({
      left: imgRect.left - bodyRect.left,
      top: imgRect.top - bodyRect.top,
      width: imgRect.width,
      height: imgRect.height,
      naturalWidth: imageRef.current.naturalWidth || 1,
      naturalHeight: imageRef.current.naturalHeight || 1,
    });
  }, []);

  useEffect(() => {
    const onResize = () => refreshImageFrame();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [refreshImageFrame]);

  useEffect(() => {
    if (!imageFrame) {
      return;
    }

    const clamped = clampBoundaries(roi, imageFrame.naturalWidth, imageFrame.naturalHeight);
    if (!sameBoundaries(clamped, roi)) {
      setRoi(clamped);
    }
  }, [imageFrame, roi, setRoi]);

  const roiDisplay = useMemo(() => {
    if (!imageFrame || regionMode === "FULL") {
      return null;
    }

    const bounds = clampBoundaries(roi, imageFrame.naturalWidth, imageFrame.naturalHeight);
    const [left, top, right, bottom] = bounds;

    const scaleX = imageFrame.width / imageFrame.naturalWidth;
    const scaleY = imageFrame.height / imageFrame.naturalHeight;

    const x = imageFrame.left + left * scaleX;
    const y = imageFrame.top + top * scaleY;
    const width = Math.max(8, (right - left + 1) * scaleX);
    const height = Math.max(8, (bottom - top + 1) * scaleY);

    return {
      x,
      y,
      width,
      height,
      bounds,
    };
  }, [imageFrame, regionMode, roi]);

  const updateTone = useCallback(
    (brightness, contrast) => {
      if (toneUpdateRef.current) {
        clearTimeout(toneUpdateRef.current);
      }

      toneUpdateRef.current = setTimeout(async () => {
        const requestToken = toneRequestCounterRef.current + 1;
        toneRequestCounterRef.current = requestToken;

        const adjustResult = await adjustBrightnessContrast(index, brightness, contrast, {
          includeImage: true,
          abortPrevious: true,
        });

        if (adjustResult?.cancelled || requestToken !== toneRequestCounterRef.current) {
          return;
        }

        await getImageComponent(index, componentType);
      }, 45);
    },
    [adjustBrightnessContrast, componentType, getImageComponent, index]
  );

  const handleToneMove = useCallback(
    (event) => {
      const drag = toneDragRef.current;
      if (!drag) {
        return;
      }

      const dx = event.clientX - drag.startX;
      const dy = drag.startY - event.clientY;
      const brightness = Math.max(-255, Math.min(255, drag.startBrightness + dy));
      const contrast = Math.max(-0.9, Math.min(3.0, drag.startContrast + dx / 200));

      setTone({ brightness, contrast });
      updateTone(brightness, contrast);
    },
    [updateTone]
  );

  const endToneDrag = useCallback(() => {
    toneDragRef.current = null;
    if (toneUpdateRef.current) {
      clearTimeout(toneUpdateRef.current);
      toneUpdateRef.current = null;
    }
    window.removeEventListener("mousemove", handleToneMove);
    window.removeEventListener("mouseup", endToneDrag);
    window.removeEventListener("blur", endToneDrag);
  }, [handleToneMove]);

  const startToneDrag = (event) => {
    if (!components[index] || event.button !== 0) {
      return;
    }

    event.preventDefault();

    toneDragRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      startBrightness: tone.brightness,
      startContrast: tone.contrast,
    };

    window.addEventListener("mousemove", handleToneMove);
    window.addEventListener("mouseup", endToneDrag);
    window.addEventListener("blur", endToneDrag);
  };

  const moveRoi = useCallback((session, deltaX, deltaY) => {
    const minSpanX = Math.min(MIN_ROI_SPAN, Math.max(1, session.naturalWidth - 1));
    const minSpanY = Math.min(MIN_ROI_SPAN, Math.max(1, session.naturalHeight - 1));
    const maxX = session.naturalWidth - 1;
    const maxY = session.naturalHeight - 1;

    let [left, top, right, bottom] = session.startBounds;

    if (!session.handle) {
      const spanX = right - left;
      const spanY = bottom - top;
      left = Math.max(0, Math.min(maxX - spanX, left + deltaX));
      top = Math.max(0, Math.min(maxY - spanY, top + deltaY));
      right = left + spanX;
      bottom = top + spanY;
    } else {
      if (session.handle.includes("w")) {
        left = Math.max(0, Math.min(right - minSpanX, left + deltaX));
      }
      if (session.handle.includes("e")) {
        right = Math.min(maxX, Math.max(left + minSpanX, right + deltaX));
      }
      if (session.handle.includes("n")) {
        top = Math.max(0, Math.min(bottom - minSpanY, top + deltaY));
      }
      if (session.handle.includes("s")) {
        bottom = Math.min(maxY, Math.max(top + minSpanY, bottom + deltaY));
      }
    }

    return clampBoundaries([left, top, right, bottom], session.naturalWidth, session.naturalHeight);
  }, []);

  const handleRoiMove = useCallback(
    (event) => {
      const session = roiDragRef.current;
      if (!session) {
        return;
      }

      const deltaX = Math.round((event.clientX - session.startClientX) * (session.naturalWidth / session.frameWidth));
      const deltaY = Math.round((event.clientY - session.startClientY) * (session.naturalHeight / session.frameHeight));
      const next = moveRoi(session, deltaX, deltaY);

      setRoi(next);
    },
    [moveRoi, setRoi]
  );

  const endRoiDrag = useCallback(() => {
    roiDragRef.current = null;

    window.removeEventListener("mousemove", handleRoiMove);
    window.removeEventListener("mouseup", endRoiDrag);
  }, [handleRoiMove]);

  const startRoiDrag = (event, handle = null) => {
    if (!roiDisplay || !imageFrame) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    roiDragRef.current = {
      handle,
      startClientX: event.clientX,
      startClientY: event.clientY,
      frameWidth: Math.max(1, imageFrame.width),
      frameHeight: Math.max(1, imageFrame.height),
      naturalWidth: imageFrame.naturalWidth,
      naturalHeight: imageFrame.naturalHeight,
      startBounds: [...roiDisplay.bounds],
    };

    window.addEventListener("mousemove", handleRoiMove);
    window.addEventListener("mouseup", endRoiDrag);
  };

  useEffect(() => {
    return () => {
      if (toneUpdateRef.current) {
        clearTimeout(toneUpdateRef.current);
      }
      window.removeEventListener("mousemove", handleToneMove);
      window.removeEventListener("mouseup", endToneDrag);
      window.removeEventListener("blur", endToneDrag);
      window.removeEventListener("mousemove", handleRoiMove);
      window.removeEventListener("mouseup", endRoiDrag);
    };
  }, [endRoiDrag, endToneDrag, handleRoiMove, handleToneMove]);

  const setType = (value) => {
    const next = [...componentTypes];
    next[index] = value;
    setComponentTypes(next);
  };

  const outerMasks = useMemo(() => {
    if (!roiDisplay || !imageFrame || activeRegionType !== "OUTER") {
      return [];
    }

    const frameLeft = imageFrame.left;
    const frameTop = imageFrame.top;
    const frameRight = imageFrame.left + imageFrame.width;
    const frameBottom = imageFrame.top + imageFrame.height;
    const roiRight = roiDisplay.x + roiDisplay.width;
    const roiBottom = roiDisplay.y + roiDisplay.height;

    const masks = [
      { left: frameLeft, top: frameTop, width: imageFrame.width, height: Math.max(0, roiDisplay.y - frameTop) },
      {
        left: frameLeft,
        top: roiDisplay.y,
        width: Math.max(0, roiDisplay.x - frameLeft),
        height: roiDisplay.height,
      },
      {
        left: roiRight,
        top: roiDisplay.y,
        width: Math.max(0, frameRight - roiRight),
        height: roiDisplay.height,
      },
      {
        left: frameLeft,
        top: roiBottom,
        width: imageFrame.width,
        height: Math.max(0, frameBottom - roiBottom),
      },
    ];

    return masks.filter((mask) => mask.width > 0 && mask.height > 0);
  }, [activeRegionType, imageFrame, roiDisplay]);

  return (
    <div className="viewer-card">
      <div className="viewer-header row-between">
        <span>FT Component {index + 1}</span>
        <select value={componentType} onChange={(e) => setType(e.target.value)}>
          <option value="magnitude">Magnitude</option>
          <option value="phase">Phase</option>
          <option value="real">Real</option>
          <option value="imaginary">Imaginary</option>
        </select>
      </div>
      <div className="viewer-body" ref={bodyRef} onMouseDown={startToneDrag}>
        {components[index] ? (
          <>
            <img
              ref={imageRef}
              src={`data:image/png;base64,${components[index]}`}
              alt={`Component ${index + 1}`}
              className="fit-image"
              onLoad={refreshImageFrame}
              draggable={false}
              onDragStart={(event) => event.preventDefault()}
            />

            {roiDisplay && (
              <>
                {activeRegionType === "INNER" && (
                  <div
                    className="roi-inner-highlight"
                    style={{
                      left: `${roiDisplay.x}px`,
                      top: `${roiDisplay.y}px`,
                      width: `${roiDisplay.width}px`,
                      height: `${roiDisplay.height}px`,
                    }}
                  />
                )}

                {activeRegionType === "OUTER" &&
                  outerMasks.map((mask, maskIndex) => (
                    <div
                      key={`outer-mask-${index}-${maskIndex}`}
                      className="roi-outer-mask"
                      style={{
                        left: `${mask.left}px`,
                        top: `${mask.top}px`,
                        width: `${mask.width}px`,
                        height: `${mask.height}px`,
                      }}
                    />
                  ))}

                <div
                  className="roi-overlay"
                  style={{
                    left: `${roiDisplay.x}px`,
                    top: `${roiDisplay.y}px`,
                    width: `${roiDisplay.width}px`,
                    height: `${roiDisplay.height}px`,
                  }}
                  onMouseDown={(event) => startRoiDrag(event)}
                >
                  <button type="button" className="roi-handle roi-handle-nw" onMouseDown={(event) => startRoiDrag(event, "nw")} />
                  <button type="button" className="roi-handle roi-handle-ne" onMouseDown={(event) => startRoiDrag(event, "ne")} />
                  <button type="button" className="roi-handle roi-handle-sw" onMouseDown={(event) => startRoiDrag(event, "sw")} />
                  <button type="button" className="roi-handle roi-handle-se" onMouseDown={(event) => startRoiDrag(event, "se")} />
                </div>
              </>
            )}
          </>
        ) : (
          <div className="placeholder">Component preview</div>
        )}
      </div>
      <div className="viewer-footer">
        <small>B {tone.brightness.toFixed(0)} / C {tone.contrast.toFixed(2)}</small>
        <small>Drag to adjust FT view</small>
      </div>
    </div>
  );
}
