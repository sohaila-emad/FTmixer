import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import axios from "axios";

const ImageMixerContext = createContext(null);
const API_BASE_URL = "/api/mixer";

export function useImageMixer() {
  const context = useContext(ImageMixerContext);
  if (!context) {
    throw new Error("useImageMixer must be used inside ImageMixerProvider");
  }
  return context;
}

export function ImageMixerProvider({ children }) {
  const [images, setImages] = useState([null, null, null, null]);
  const [components, setComponents] = useState([null, null, null, null]);
  const [componentTypes, setComponentTypes] = useState(["magnitude", "magnitude", "magnitude", "magnitude"]);

  const [weights, setWeights] = useState([25, 25, 25, 25]);
  const [imageModes, setImageModes] = useState(["MAGNITUDE", "MAGNITUDE", "MAGNITUDE", "MAGNITUDE"]);
  const [mixingMode, setMixingMode] = useState("MAGNITUDE_PHASE");
  const [regionMode, setRegionMode] = useState("FULL");
  const [imageRegionModes, setImageRegionModes] = useState(["INNER", "INNER", "INNER", "INNER"]);
  const [roi, setRoi] = useState([0, 0, 100, 100]);

  const [outputImages, setOutputImages] = useState([null, null]);
  const [currentOutputViewer, setCurrentOutputViewer] = useState(0);

  const [sizePolicy, setSizePolicy] = useState("smallest");
  const [keepAspectRatio, setKeepAspectRatio] = useState(false);
  const [fixedSize, setFixedSize] = useState({ width: 512, height: 512 });

  const [simulateBottleneck, setSimulateBottleneck] = useState(false);
  const [bottleneckSeconds, setBottleneckSeconds] = useState(2);

  const [isMixing, setIsMixing] = useState(false);
  const [mixingProgress, setMixingProgress] = useState(0);
  const pollingRef = useRef(null);
  const requestIdRef = useRef(0);
  const brightnessAbortControllersRef = useRef([null, null, null, null]);

  const weightsRef = useRef(weights);
  const imageModesRef = useRef(imageModes);
  const mixingModeRef = useRef(mixingMode);
  const regionModeRef = useRef(regionMode);
  const imageRegionModesRef = useRef(imageRegionModes);
  const roiRef = useRef(roi);
  const currentOutputViewerRef = useRef(currentOutputViewer);

  useEffect(() => {
    weightsRef.current = weights;
  }, [weights]);

  useEffect(() => {
    imageModesRef.current = imageModes;
  }, [imageModes]);

  useEffect(() => {
    mixingModeRef.current = mixingMode;
  }, [mixingMode]);

  useEffect(() => {
    regionModeRef.current = regionMode;
  }, [regionMode]);

  useEffect(() => {
    imageRegionModesRef.current = imageRegionModes;
  }, [imageRegionModes]);

  useEffect(() => {
    roiRef.current = roi;
  }, [roi]);

  useEffect(() => {
    currentOutputViewerRef.current = currentOutputViewer;
  }, [currentOutputViewer]);

  useEffect(() => {
    const allowed = mixingMode === "MAGNITUDE_PHASE" ? ["MAGNITUDE", "PHASE"] : ["REAL", "IMAGINARY"];
    const fallback = allowed[0];
    setImageModes((prev) => {
      const next = prev.map((mode) => (allowed.includes(mode) ? mode : fallback));
      const changed = next.some((mode, idx) => mode !== prev[idx]);
      return changed ? next : prev;
    });
  }, [mixingMode]);

  useEffect(() => {
    return () => {
      requestIdRef.current += 1;
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  const uploadImage = useCallback(async (file, imageIndex) => {
    const formData = new FormData();
    formData.append("image", file);
    formData.append("image_index", imageIndex);

    const response = await axios.post(`${API_BASE_URL}/upload-image/`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    if (response.data.success) {
      if (Array.isArray(response.data.images_data) && response.data.images_data.length === 4) {
        setImages(response.data.images_data);
      } else {
        setImages((prev) => {
          const next = [...prev];
          next[imageIndex] = response.data.image_data;
          return next;
        });
      }
      return { success: true };
    }

    return { success: false, error: response.data.error || "Upload failed" };
  }, []);

  const uploadMultipleImages = useCallback(async (files) => {
    const list = Array.from(files).slice(0, 4);
    for (let i = 0; i < list.length; i += 1) {
      const res = await uploadImage(list[i], i);
      if (!res.success) {
        return res;
      }
    }
    return { success: true };
  }, [uploadImage]);

  const getImageComponent = useCallback(async (imageIndex, componentType) => {
    const response = await axios.get(`${API_BASE_URL}/image/${imageIndex}/component/${componentType}/`);
    if (response.data.success) {
      setComponents((prev) => {
        const next = [...prev];
        next[imageIndex] = response.data.image_data;
        return next;
      });
      return { success: true };
    }
    return { success: false, error: response.data.error || "Component load failed" };
  }, []);

  const adjustBrightnessContrast = useCallback(async (imageIndex, brightness, contrast, options = {}) => {
    const { includeImage = false, abortPrevious = true } = options;

    if (abortPrevious) {
      const previousController = brightnessAbortControllersRef.current[imageIndex];
      if (previousController) {
        previousController.abort();
      }
    }

    const controller = new AbortController();
    brightnessAbortControllersRef.current[imageIndex] = controller;

    try {
      const response = await axios.post(
        `${API_BASE_URL}/adjust-brightness-contrast/`,
        {
          image_index: imageIndex,
          brightness,
          contrast,
          include_image: includeImage,
        },
        { signal: controller.signal }
      );

      if (response.data.success) {
        if (includeImage && response.data.image_data) {
          setImages((prev) => {
            const next = [...prev];
            next[imageIndex] = response.data.image_data;
            return next;
          });
        }
        return { success: true };
      }

      return { success: false, error: response.data.error || "Adjustment failed" };
    } catch (error) {
      if (error?.name === "CanceledError" || error?.code === "ERR_CANCELED") {
        return { success: false, cancelled: true };
      }
      return { success: false, error: error.message || "Adjustment failed" };
    } finally {
      if (brightnessAbortControllersRef.current[imageIndex] === controller) {
        brightnessAbortControllersRef.current[imageIndex] = null;
      }
    }
  }, []);

  const cancelBrightnessAdjustments = useCallback((imageIndex) => {
    const controller = brightnessAbortControllersRef.current[imageIndex];
    if (controller) {
      controller.abort();
      brightnessAbortControllersRef.current[imageIndex] = null;
    }
  }, []);

  const resetBrightnessContrast = useCallback(async (imageIndex) => {
    cancelBrightnessAdjustments(imageIndex);

    const response = await axios.post(`${API_BASE_URL}/reset-brightness-contrast/`, {
      image_index: imageIndex,
    });

    if (response.data.success) {
      setImages((prev) => {
        const next = [...prev];
        next[imageIndex] = response.data.image_data;
        return next;
      });
      return { success: true };
    }

    return { success: false, error: response.data.error || "Reset failed" };
  }, [cancelBrightnessAdjustments]);

  const setBackendModes = useCallback(async () => {
    await axios.post(`${API_BASE_URL}/set-mixing-mode/`, { mode: mixingModeRef.current });
    await Promise.all(
      imageModesRef.current.map((mode, idx) =>
        axios.post(`${API_BASE_URL}/set-image-mode/`, {
          image_index: idx,
          mode,
        })
      )
    );
  }, []);

  const applyImageSizing = useCallback(async (overrides = {}) => {
    const policy = overrides.policy ?? sizePolicy;
    const keepAspect = overrides.keepAspectRatio ?? keepAspectRatio;
    const width = Number(overrides.fixedWidth ?? fixedSize.width);
    const height = Number(overrides.fixedHeight ?? fixedSize.height);
    const applyNow = overrides.applyNow ?? true;

    const payload = {
      policy,
      keep_aspect_ratio: keepAspect,
      apply_now: applyNow,
    };

    if (policy === "fixed") {
      payload.fixed_width = width;
      payload.fixed_height = height;
    }

    const response = await axios.post(`${API_BASE_URL}/set-image-sizing/`, payload);
    if (!response.data.success) {
      return { success: false, error: response.data.error || "Failed to update image sizing" };
    }

    const sizing = response.data.sizing || {};
    setSizePolicy(sizing.policy || policy);
    setKeepAspectRatio(Boolean(sizing.keep_aspect_ratio ?? keepAspect));
    setFixedSize({
      width: Number(sizing.fixed_width ?? width),
      height: Number(sizing.fixed_height ?? height),
    });

    if (Array.isArray(response.data.images_data) && response.data.images_data.length === 4) {
      setImages(response.data.images_data);
    }

    return { success: true };
  }, [fixedSize.height, fixedSize.width, keepAspectRatio, sizePolicy]);

  const applyProcessingOptions = useCallback(async () => {
    const response = await axios.post(`${API_BASE_URL}/set-processing-options/`, {
      simulate_bottleneck: simulateBottleneck,
      bottleneck_seconds: bottleneckSeconds,
    });

    if (!response.data.success) {
      return { success: false, error: response.data.error || "Failed to update processing options" };
    }
    return { success: true };
  }, [bottleneckSeconds, simulateBottleneck]);

  const mixImages = useCallback(async (overrideRoi = null, overrideOutputViewer = null) => {
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;

    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    try {
      await axios.post(`${API_BASE_URL}/mix-cancel/`);
    } catch (_cancelError) {
      // Cancel endpoint is best effort for replacing in-flight tasks.
    }

    try {
      const processingResult = await applyProcessingOptions();
      if (!processingResult.success) {
        return processingResult;
      }

      await setBackendModes();
      if (requestId !== requestIdRef.current) {
        return { success: false, error: "Superseded by a newer request" };
      }

      const targetOutputViewer =
        typeof overrideOutputViewer === "number" ? overrideOutputViewer : currentOutputViewerRef.current;
      const boundariesToUse = Array.isArray(overrideRoi) ? overrideRoi : roiRef.current;

      setIsMixing(true);
      setMixingProgress(0);

      await axios.post(`${API_BASE_URL}/mix/`, {
        weights: weightsRef.current,
        boundaries: boundariesToUse,
        region_mode: regionModeRef.current,
        image_region_modes: imageRegionModesRef.current,
        output_viewer: targetOutputViewer,
        current_mode: mixingModeRef.current,
      });

      if (requestId !== requestIdRef.current) {
        return { success: false, error: "Superseded by a newer request" };
      }

      return new Promise((resolve) => {
        pollingRef.current = setInterval(async () => {
          try {
            if (requestId !== requestIdRef.current) {
              clearInterval(pollingRef.current);
              pollingRef.current = null;
              resolve({ success: false, error: "Superseded by a newer request" });
              return;
            }

            const statusResponse = await axios.get(`${API_BASE_URL}/mix-status/`);
            if (!statusResponse.data.success) {
              return;
            }

            const { is_mixing, progress, error } = statusResponse.data;
            setMixingProgress(progress ?? 0);

            if (error) {
              clearInterval(pollingRef.current);
              pollingRef.current = null;
              if (requestId === requestIdRef.current) {
                setIsMixing(false);
              }
              resolve({ success: false, error });
              return;
            }

            if (!is_mixing && (progress ?? 0) >= 100) {
              clearInterval(pollingRef.current);
              pollingRef.current = null;

              const resultResponse = await axios.get(`${API_BASE_URL}/mix-result/`, {
                params: { output_viewer: targetOutputViewer },
              });

              if (resultResponse.data.success) {
                if (requestId === requestIdRef.current) {
                  setOutputImages((prev) => {
                    const next = [...prev];
                    next[targetOutputViewer] = resultResponse.data.image_data;
                    return next;
                  });
                  setIsMixing(false);
                  setTimeout(() => {
                    if (requestId === requestIdRef.current) {
                      setMixingProgress(0);
                    }
                  }, 400);
                }
                resolve({ success: true });
                return;
              }

              if (requestId === requestIdRef.current) {
                setIsMixing(false);
              }
              resolve({ success: false, error: "Failed to fetch mix result" });
            }
          } catch (error) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
            if (requestId === requestIdRef.current) {
              setIsMixing(false);
            }
            resolve({ success: false, error: error.message });
          }
        }, 140);
      });
    } catch (error) {
      if (requestId === requestIdRef.current) {
        setIsMixing(false);
        setMixingProgress(0);
      }
      return { success: false, error: error.message };
    }
  }, [applyProcessingOptions, setBackendModes]);

  const value = {
    images,
    setImages,
    components,
    componentTypes,
    setComponentTypes,
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
    outputImages,
    currentOutputViewer,
    setCurrentOutputViewer,
    sizePolicy,
    setSizePolicy,
    keepAspectRatio,
    setKeepAspectRatio,
    fixedSize,
    setFixedSize,
    applyImageSizing,
    simulateBottleneck,
    setSimulateBottleneck,
    bottleneckSeconds,
    setBottleneckSeconds,
    isMixing,
    mixingProgress,
    uploadImage,
    uploadMultipleImages,
    getImageComponent,
    adjustBrightnessContrast,
    cancelBrightnessAdjustments,
    resetBrightnessContrast,
    mixImages,
  };

  return <ImageMixerContext.Provider value={value}>{children}</ImageMixerContext.Provider>;
}
