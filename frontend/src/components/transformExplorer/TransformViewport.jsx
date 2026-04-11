import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTransformExplorer } from "./TransformExplorerContext";

const COMPONENT_OPTIONS = ["magnitude", "phase", "real", "imaginary"];

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

export function TransformViewport({ viewportKey, title }) {
  const {
    viewports,
    componentSelections,
    setViewportComponent,
    selectedOperationId,
    domain,
    parameterValues,
    setParamValue,
    uploadSource,
    isApplying,
  } = useTransformExplorer();

  const imageRef = useRef(null);
  const bodyRef = useRef(null);
  const fileRef = useRef(null);
  const moveRef = useRef(null);
  const resizeRef = useRef(null);

  const [imageFrame, setImageFrame] = useState(null);
  const [kernelSize, setKernelSize] = useState({ width: 31, height: 31 });
  const [kernelCenter, setKernelCenter] = useState({ x: 0.5, y: 0.5 });

  const componentName = componentSelections[viewportKey] || "magnitude";
  const viewportData = viewports[viewportKey];
  const imageData = viewportData?.[componentName] || null;

  const isUploadViewport = viewportKey === "spatial_original";
  const isWindowOverlayTarget =
    selectedOperationId === "window_multiply" &&
    ((domain === "spatial" && viewportKey === "spatial_original") ||
      (domain === "frequency" && viewportKey === "frequency_original"));

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
    if (!isWindowOverlayTarget) {
      return;
    }

    const nextWidth = Math.max(1, Math.round(Number(parameterValues.kernel_width ?? kernelSize.width)));
    const nextHeight = Math.max(1, Math.round(Number(parameterValues.kernel_height ?? kernelSize.height)));
    if (nextWidth !== kernelSize.width || nextHeight !== kernelSize.height) {
      setKernelSize({ width: nextWidth, height: nextHeight });
    }
  }, [isWindowOverlayTarget, kernelSize.height, kernelSize.width, parameterValues.kernel_height, parameterValues.kernel_width]);

  const onMoveOverlay = useCallback((event) => {
    const session = moveRef.current;
    if (!session) {
      return;
    }

    const dx = event.clientX - session.startX;
    const dy = event.clientY - session.startY;
    setKernelCenter({
      x: clamp(session.startCenterX + (dx / session.frameWidth), 0, 1),
      y: clamp(session.startCenterY + (dy / session.frameHeight), 0, 1),
    });
  }, []);

  const stopMove = useCallback(() => {
    moveRef.current = null;
    window.removeEventListener("mousemove", onMoveOverlay);
    window.removeEventListener("mouseup", stopMove);
  }, [onMoveOverlay]);

  const startMove = (event) => {
    if (!isWindowOverlayTarget || !imageFrame) {
      return;
    }

    event.preventDefault();
    moveRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      frameWidth: Math.max(1, imageFrame.width),
      frameHeight: Math.max(1, imageFrame.height),
      startCenterX: kernelCenter.x,
      startCenterY: kernelCenter.y,
    };
    window.addEventListener("mousemove", onMoveOverlay);
    window.addEventListener("mouseup", stopMove);
  };

  const onResizeMove = useCallback((event) => {
    const session = resizeRef.current;
    if (!session) {
      return;
    }

    const dx = event.clientX - session.startX;
    const dy = event.clientY - session.startY;
    const nextWidth = Math.max(1, Math.round(session.startWidth + (dx / session.scaleX)));
    const nextHeight = Math.max(1, Math.round(session.startHeight + (dy / session.scaleY)));

    setKernelSize({ width: nextWidth, height: nextHeight });
    setParamValue("kernel_width", nextWidth);
    setParamValue("kernel_height", nextHeight);
  }, [setParamValue]);

  const stopResize = useCallback(() => {
    resizeRef.current = null;
    window.removeEventListener("mousemove", onResizeMove);
    window.removeEventListener("mouseup", stopResize);
  }, [onResizeMove]);

  const startResize = (event) => {
    if (!isWindowOverlayTarget || !imageFrame) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    resizeRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      startWidth: kernelSize.width,
      startHeight: kernelSize.height,
      scaleX: imageFrame.width / Math.max(1, imageFrame.naturalWidth),
      scaleY: imageFrame.height / Math.max(1, imageFrame.naturalHeight),
    };
    window.addEventListener("mousemove", onResizeMove);
    window.addEventListener("mouseup", stopResize);
  };

  useEffect(() => {
    return () => {
      window.removeEventListener("mousemove", onMoveOverlay);
      window.removeEventListener("mouseup", stopMove);
      window.removeEventListener("mousemove", onResizeMove);
      window.removeEventListener("mouseup", stopResize);
    };
  }, [onMoveOverlay, stopMove, onResizeMove, stopResize]);

  const overlayStyle = useMemo(() => {
    if (!imageFrame || !isWindowOverlayTarget) {
      return null;
    }

    const scaleX = imageFrame.width / Math.max(1, imageFrame.naturalWidth);
    const scaleY = imageFrame.height / Math.max(1, imageFrame.naturalHeight);
    const displayWidth = Math.max(10, kernelSize.width * scaleX);
    const displayHeight = Math.max(10, kernelSize.height * scaleY);

    const maxLeft = Math.max(0, imageFrame.width - displayWidth);
    const maxTop = Math.max(0, imageFrame.height - displayHeight);
    const left = imageFrame.left + clamp((kernelCenter.x * imageFrame.width) - (displayWidth / 2), 0, maxLeft);
    const top = imageFrame.top + clamp((kernelCenter.y * imageFrame.height) - (displayHeight / 2), 0, maxTop);

    return {
      left: `${left}px`,
      top: `${top}px`,
      width: `${displayWidth}px`,
      height: `${displayHeight}px`,
    };
  }, [imageFrame, isWindowOverlayTarget, kernelCenter.x, kernelCenter.y, kernelSize.height, kernelSize.width]);

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

      <div
        className="viewer-body"
        ref={bodyRef}
        onDoubleClick={() => {
          if (isUploadViewport) {
            fileRef.current?.click();
          }
        }}
      >
        {imageData ? (
          <>
            <img
              ref={imageRef}
              src={`data:image/png;base64,${imageData}`}
              alt={`${title} ${componentName}`}
              className="fit-image"
              onLoad={refreshImageFrame}
              draggable={false}
              onDragStart={(event) => event.preventDefault()}
            />
            {overlayStyle ? (
              <div className="roi-overlay" style={overlayStyle} onMouseDown={startMove}>
                <button type="button" className="roi-handle roi-handle-se" onMouseDown={startResize} />
              </div>
            ) : null}
          </>
        ) : (
          <div className="placeholder">{isUploadViewport ? "Double-click to load source image" : "No data yet"}</div>
        )}

        {isUploadViewport ? (
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
            disabled={isApplying}
          />
        ) : null}
      </div>
    </div>
  );
}
