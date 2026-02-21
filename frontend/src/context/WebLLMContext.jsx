import { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";

// WebLLM Context for global state management
const WebLLMContext = createContext(null);

// Model configuration - Use 360M model for better stability on mobile/low VRAM devices
const MODEL_ID = "SmolLM2-360M-Instruct-q4f32_1-MLC";
const MODEL_SIZE_GB = 0.6;

// LocalStorage keys
const STORAGE_KEYS = {
  MODEL_CACHED: "webllm_model_cached",
  DOWNLOAD_STARTED: "webllm_download_started",
  DOWNLOAD_PROGRESS: "webllm_download_progress",
  USER_INITIATED: "webllm_user_initiated"
};

// Check WebGPU support
const checkWebGPUSupport = async () => {
  if (typeof navigator === "undefined" || !navigator.gpu) {
    return { supported: false, reason: "WebGPU non supporté par ce navigateur" };
  }
  
  try {
    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) {
      return { supported: false, reason: "Aucun adaptateur GPU disponible" };
    }
    
    const device = await adapter.requestDevice();
    if (!device) {
      return { supported: false, reason: "Impossible d'initialiser le GPU" };
    }
    
    return { supported: true };
  } catch (e) {
    return { supported: false, reason: e.message };
  }
};

// Check if model is already cached in IndexedDB
const checkModelCached = async () => {
  try {
    // Check localStorage flag first (quick check)
    const cachedFlag = localStorage.getItem(STORAGE_KEYS.MODEL_CACHED);
    if (cachedFlag === "true") {
      // Verify IndexedDB actually has the model
      const { hasModelInCache } = await import("@mlc-ai/web-llm");
      const isCached = await hasModelInCache(MODEL_ID);
      if (!isCached) {
        localStorage.removeItem(STORAGE_KEYS.MODEL_CACHED);
        return false;
      }
      return true;
    }
    return false;
  } catch (e) {
    console.error("Error checking model cache:", e);
    return false;
  }
};

export const WebLLMProvider = ({ children }) => {
  // State
  const [webGPUSupported, setWebGPUSupported] = useState(null);
  const [modelCached, setModelCached] = useState(false);
  const [modelLoaded, setModelLoaded] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [downloadStatus, setDownloadStatus] = useState("");
  const [error, setError] = useState(null);
  const [showFirstTimeBanner, setShowFirstTimeBanner] = useState(false);
  const [userInitiated, setUserInitiated] = useState(false);
  
  // Refs
  const engineRef = useRef(null);
  const downloadAbortRef = useRef(false);
  
  // Check WebGPU and cache status on mount
  useEffect(() => {
    const init = async () => {
      // Check WebGPU support
      const gpuCheck = await checkWebGPUSupport();
      setWebGPUSupported(gpuCheck.supported);
      
      if (!gpuCheck.supported) {
        console.log("WebGPU not supported:", gpuCheck.reason);
        return;
      }
      
      // Check if model is already cached
      const isCached = await checkModelCached();
      setModelCached(isCached);
      
      // Check if download was in progress (for resume)
      const downloadStarted = localStorage.getItem(STORAGE_KEYS.DOWNLOAD_STARTED);
      const previousProgress = localStorage.getItem(STORAGE_KEYS.DOWNLOAD_PROGRESS);
      const wasUserInitiated = localStorage.getItem(STORAGE_KEYS.USER_INITIATED);
      
      if (downloadStarted === "true" && !isCached && wasUserInitiated === "true") {
        // Resume download
        setUserInitiated(true);
        setDownloadProgress(parseInt(previousProgress) || 0);
        setDownloadStatus("Reprise du téléchargement...");
        // Will auto-resume in the next useEffect
      }
      
      // Show first-time banner if not cached and never seen
      if (!isCached && !localStorage.getItem("webllm_banner_dismissed")) {
        setShowFirstTimeBanner(true);
      }
    };
    
    init();
  }, []);
  
  // Auto-resume download if user had initiated it
  useEffect(() => {
    const resumeDownload = async () => {
      const downloadStarted = localStorage.getItem(STORAGE_KEYS.DOWNLOAD_STARTED);
      const wasUserInitiated = localStorage.getItem(STORAGE_KEYS.USER_INITIATED);
      
      if (downloadStarted === "true" && wasUserInitiated === "true" && !modelCached && webGPUSupported && !isDownloading) {
        console.log("Resuming WebLLM download...");
        await startDownload();
      }
    };
    
    if (webGPUSupported !== null) {
      resumeDownload();
    }
  }, [webGPUSupported, modelCached]);
  
  // Start/Resume download
  const startDownload = useCallback(async () => {
    if (!webGPUSupported || isDownloading) return false;
    
    setIsDownloading(true);
    setError(null);
    setUserInitiated(true);
    downloadAbortRef.current = false;
    
    // Save state for resume
    localStorage.setItem(STORAGE_KEYS.DOWNLOAD_STARTED, "true");
    localStorage.setItem(STORAGE_KEYS.USER_INITIATED, "true");
    
    try {
      const { CreateMLCEngine } = await import("@mlc-ai/web-llm");
      
      // Progress callback
      const progressCallback = (progress) => {
        if (downloadAbortRef.current) return;
        
        const pct = Math.round(progress.progress * 100);
        setDownloadProgress(pct);
        setDownloadStatus(progress.text || `Téléchargement: ${pct}%`);
        
        // Save progress for resume
        localStorage.setItem(STORAGE_KEYS.DOWNLOAD_PROGRESS, pct.toString());
      };
      
      // Create engine (this downloads and caches the model)
      engineRef.current = await CreateMLCEngine(MODEL_ID, {
        initProgressCallback: progressCallback,
      });
      
      if (downloadAbortRef.current) {
        throw new Error("Download cancelled");
      }
      
      // Success!
      setModelLoaded(true);
      setModelCached(true);
      setDownloadStatus("Coach IA local prêt !");
      
      // Update localStorage
      localStorage.setItem(STORAGE_KEYS.MODEL_CACHED, "true");
      localStorage.removeItem(STORAGE_KEYS.DOWNLOAD_STARTED);
      localStorage.removeItem(STORAGE_KEYS.DOWNLOAD_PROGRESS);
      
      return true;
    } catch (err) {
      console.error("WebLLM download error:", err);
      
      if (err.message !== "Download cancelled") {
        setError(err.message || "Erreur lors du téléchargement");
        // Keep download state for potential resume
      }
      
      return false;
    } finally {
      setIsDownloading(false);
    }
  }, [webGPUSupported, isDownloading]);
  
  // Load model from cache (fast, no download needed)
  const loadFromCache = useCallback(async () => {
    if (!webGPUSupported || !modelCached || modelLoaded) return false;
    
    setIsDownloading(true);
    setDownloadStatus("Chargement du modèle...");
    setError(null);
    
    try {
      const { CreateMLCEngine } = await import("@mlc-ai/web-llm");
      
      engineRef.current = await CreateMLCEngine(MODEL_ID, {
        initProgressCallback: (progress) => {
          setDownloadProgress(Math.round(progress.progress * 100));
          setDownloadStatus(progress.text || "Chargement...");
        },
      });
      
      setModelLoaded(true);
      setDownloadStatus("Coach IA local prêt !");
      return true;
    } catch (err) {
      console.error("WebLLM load error:", err);
      setError(err.message || "Erreur lors du chargement");
      return false;
    } finally {
      setIsDownloading(false);
    }
  }, [webGPUSupported, modelCached, modelLoaded]);
  
  // Cancel download
  const cancelDownload = useCallback(() => {
    downloadAbortRef.current = true;
    setIsDownloading(false);
    setDownloadStatus("");
    localStorage.removeItem(STORAGE_KEYS.DOWNLOAD_STARTED);
    localStorage.removeItem(STORAGE_KEYS.USER_INITIATED);
  }, []);
  
  // Dismiss first-time banner
  const dismissBanner = useCallback(() => {
    setShowFirstTimeBanner(false);
    localStorage.setItem("webllm_banner_dismissed", "true");
  }, []);
  
  // Generate response with timeout
  const generateResponse = useCallback(async (messages, options = {}) => {
    if (!engineRef.current || !modelLoaded) {
      throw new Error("Modèle non chargé");
    }
    
    const timeout = options.timeout || 30000; // 30 seconds default timeout
    
    // Create a promise that rejects after timeout
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error("Timeout: génération trop longue")), timeout);
    });
    
    // Race between generation and timeout
    const generationPromise = engineRef.current.chat.completions.create({
      messages,
      max_tokens: options.maxTokens || 300,
      temperature: options.temperature || 0.7,
      top_p: options.topP || 0.9,
    });
    
    try {
      const response = await Promise.race([generationPromise, timeoutPromise]);
      return response.choices[0].message.content;
    } catch (err) {
      console.error("WebLLM generation error:", err);
      throw err;
    }
  }, [modelLoaded]);
  
  // Context value
  const value = {
    // State
    webGPUSupported,
    modelCached,
    modelLoaded,
    isDownloading,
    downloadProgress,
    downloadStatus,
    error,
    showFirstTimeBanner,
    userInitiated,
    
    // Constants
    modelId: MODEL_ID,
    modelSizeGB: MODEL_SIZE_GB,
    
    // Actions
    startDownload,
    loadFromCache,
    cancelDownload,
    dismissBanner,
    generateResponse,
    
    // Engine ref (for advanced usage)
    engine: engineRef.current,
  };
  
  return (
    <WebLLMContext.Provider value={value}>
      {children}
    </WebLLMContext.Provider>
  );
};

// Hook to use WebLLM context
export const useWebLLM = () => {
  const context = useContext(WebLLMContext);
  if (!context) {
    throw new Error("useWebLLM must be used within a WebLLMProvider");
  }
  return context;
};

export default WebLLMContext;
