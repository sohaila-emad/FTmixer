import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";

const TransformExplorerContext = createContext(null);
const API_BASE_URL = "/api/mixer/partb";

const EMPTY_VIEWPORTS = {
  spatial_original: null,
  spatial_transformed: null,
  frequency_original: null,
  frequency_transformed: null,
};

const DEFAULT_COMPONENTS = {
  spatial_original: "magnitude",
  spatial_transformed: "magnitude",
  frequency_original: "magnitude",
  frequency_transformed: "magnitude",
};

export function useTransformExplorer() {
  const context = useContext(TransformExplorerContext);
  if (!context) {
    throw new Error("useTransformExplorer must be used inside TransformExplorerProvider");
  }
  return context;
}

function buildDefaultParams(operation) {
  if (!operation || !Array.isArray(operation.parameters)) {
    return {};
  }

  return operation.parameters.reduce((acc, field) => {
    acc[field.id] = field.default;
    return acc;
  }, {});
}

export function TransformExplorerProvider({ children }) {
  const [operations, setOperations] = useState([]);
  const [selectedOperationId, setSelectedOperationId] = useState("");
  const [parameterValues, setParameterValues] = useState({});

  const [domain, setDomain] = useState("spatial");
  const [repeatFourier, setRepeatFourier] = useState(0);

  const [viewports, setViewports] = useState(EMPTY_VIEWPORTS);
  const [componentSelections, setComponentSelections] = useState(DEFAULT_COMPONENTS);

  const [isApplying, setIsApplying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [hasSource, setHasSource] = useState(false);

  const pollRef = useRef(null);
  const requestIdRef = useRef(0);

  const selectedOperation = useMemo(
    () => operations.find((op) => op.id === selectedOperationId) || null,
    [operations, selectedOperationId]
  );

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const fetchOperations = useCallback(async () => {
    const response = await axios.get(`${API_BASE_URL}/operations/`);
    if (!response.data.success) {
      throw new Error("Failed to load operations");
    }

    const loadedOps = response.data.operations || [];
    setOperations(loadedOps);

    if (loadedOps.length > 0) {
      setSelectedOperationId((prev) => prev || loadedOps[0].id);
      setParameterValues((prev) => {
        if (Object.keys(prev).length > 0) {
          return prev;
        }
        return buildDefaultParams(loadedOps[0]);
      });
    }
  }, []);

  const fetchViewports = useCallback(async () => {
    const response = await axios.get(`${API_BASE_URL}/viewports/`);
    if (!response.data.success) {
      throw new Error("Failed to fetch viewports");
    }

    const payload = response.data.viewports || EMPTY_VIEWPORTS;
    setViewports(payload);
    setHasSource(Boolean(payload.spatial_original));
  }, []);

  useEffect(() => {
    fetchOperations().catch((err) => {
      setError(err.message || "Failed to initialize Part B");
    });

    return () => {
      requestIdRef.current += 1;
      stopPolling();
    };
  }, [fetchOperations, stopPolling]);

  useEffect(() => {
    if (!selectedOperation) {
      return;
    }
    setParameterValues(buildDefaultParams(selectedOperation));
  }, [selectedOperationId, selectedOperation]);

  const setParamValue = useCallback((paramId, value) => {
    setParameterValues((prev) => ({ ...prev, [paramId]: value }));
  }, []);

  const setViewportComponent = useCallback((viewportKey, componentName) => {
    setComponentSelections((prev) => ({
      ...prev,
      [viewportKey]: componentName,
    }));
  }, []);

  const uploadSource = useCallback(async (file) => {
    setError("");
    const formData = new FormData();
    formData.append("image", file);

    const response = await axios.post(`${API_BASE_URL}/upload-source/`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    if (!response.data.success) {
      throw new Error(response.data.error || "Upload failed");
    }

    setViewports(response.data.viewports || EMPTY_VIEWPORTS);
    setHasSource(true);
  }, []);

  const applyOperation = useCallback(async () => {
    if (!selectedOperationId) {
      setError("Choose an operation first");
      return { success: false, error: "No operation selected" };
    }

    setError("");

    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;

    stopPolling();

    try {
      await axios.post(`${API_BASE_URL}/cancel/`);
    } catch (_ignored) {
      // best effort cancellation
    }

    setIsApplying(true);
    setProgress(0);

    try {
      const response = await axios.post(`${API_BASE_URL}/apply/`, {
        operation_id: selectedOperationId,
        domain,
        params: parameterValues,
        repeat_fourier: Number(repeatFourier) || 0,
      });

      if (!response.data.success) {
        throw new Error(response.data.error || "Apply failed to start");
      }

      return await new Promise((resolve) => {
        pollRef.current = setInterval(async () => {
          try {
            if (requestId !== requestIdRef.current) {
              stopPolling();
              resolve({ success: false, error: "Superseded by newer request" });
              return;
            }

            const statusResponse = await axios.get(`${API_BASE_URL}/status/`);
            if (!statusResponse.data.success) {
              return;
            }

            setProgress(statusResponse.data.progress || 0);

            if (statusResponse.data.error) {
              stopPolling();
              setError(statusResponse.data.error);
              setIsApplying(false);
              resolve({ success: false, error: statusResponse.data.error });
              return;
            }

            if (!statusResponse.data.is_processing && (statusResponse.data.progress || 0) >= 100) {
              stopPolling();
              await fetchViewports();
              setIsApplying(false);
              setTimeout(() => {
                if (requestId === requestIdRef.current) {
                  setProgress(0);
                }
              }, 300);
              resolve({ success: true });
            }
          } catch (err) {
            stopPolling();
            setError(err.message || "Failed while polling apply status");
            setIsApplying(false);
            resolve({ success: false, error: err.message || "Polling failed" });
          }
        }, 130);
      });
    } catch (err) {
      setIsApplying(false);
      setProgress(0);
      setError(err.message || "Failed to apply operation");
      return { success: false, error: err.message || "Apply failed" };
    }
  }, [domain, fetchViewports, parameterValues, repeatFourier, selectedOperationId, stopPolling]);

  const value = {
    operations,
    selectedOperation,
    selectedOperationId,
    setSelectedOperationId,
    parameterValues,
    setParamValue,
    domain,
    setDomain,
    repeatFourier,
    setRepeatFourier,
    viewports,
    componentSelections,
    setViewportComponent,
    isApplying,
    progress,
    error,
    hasSource,
    uploadSource,
    fetchViewports,
    applyOperation,
  };

  return <TransformExplorerContext.Provider value={value}>{children}</TransformExplorerContext.Provider>;
}
