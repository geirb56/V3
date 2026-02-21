import { useState } from "react";
import { useWebLLM } from "@/context/WebLLMContext";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { 
  Download, 
  X, 
  Cpu, 
  CheckCircle, 
  AlertTriangle,
  Wifi,
  Shield,
  Sparkles
} from "lucide-react";

// First-time explanatory banner
export const WebLLMFirstTimeBanner = () => {
  const { 
    webGPUSupported, 
    showFirstTimeBanner, 
    dismissBanner, 
    startDownload,
    modelCached 
  } = useWebLLM();
  
  if (!showFirstTimeBanner || !webGPUSupported || modelCached) return null;
  
  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-amber-500/95 to-orange-500/95 text-white p-4 shadow-lg">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
            <Sparkles className="w-6 h-6" />
          </div>
          
          <div className="flex-1">
            <h3 className="font-bold text-lg mb-1">
              🚀 Coach IA local disponible !
            </h3>
            <p className="text-white/90 text-sm mb-3">
              Téléchargement unique du coach IA local (~2.7 Go) – Wi-Fi recommandé.
              <br />
              <span className="font-medium">Ça arrive une seule fois, ensuite tout est offline et privé !</span>
            </p>
            
            <div className="flex flex-wrap items-center gap-3 text-xs text-white/80 mb-4">
              <div className="flex items-center gap-1">
                <Wifi className="w-3.5 h-3.5" />
                <span>Wi-Fi recommandé</span>
              </div>
              <div className="flex items-center gap-1">
                <Shield className="w-3.5 h-3.5" />
                <span>100% privé</span>
              </div>
              <div className="flex items-center gap-1">
                <Cpu className="w-3.5 h-3.5" />
                <span>Fonctionne offline</span>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <Button 
                onClick={() => {
                  dismissBanner();
                  startDownload();
                }}
                className="bg-white text-amber-600 hover:bg-white/90"
              >
                <Download className="w-4 h-4 mr-2" />
                Télécharger maintenant
              </Button>
              <Button 
                variant="ghost" 
                onClick={dismissBanner}
                className="text-white/80 hover:text-white hover:bg-white/10"
              >
                Plus tard
              </Button>
            </div>
          </div>
          
          <button 
            onClick={dismissBanner}
            className="text-white/60 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

// Persistent download progress banner
export const WebLLMDownloadBanner = () => {
  const { 
    isDownloading, 
    downloadProgress, 
    downloadStatus, 
    error,
    modelLoaded,
    cancelDownload,
    userInitiated
  } = useWebLLM();
  
  const [minimized, setMinimized] = useState(false);
  
  // Only show if user has initiated download and it's in progress or just completed
  if (!userInitiated || (!isDownloading && !modelLoaded && !error)) return null;
  
  // Hide after model is loaded (with delay for success message)
  if (modelLoaded && downloadProgress === 100) {
    // Show success briefly then hide
    setTimeout(() => {}, 3000);
  }
  
  if (minimized) {
    return (
      <button
        onClick={() => setMinimized(false)}
        className="fixed bottom-20 md:bottom-4 right-4 z-40 bg-amber-500 text-white p-3 rounded-full shadow-lg hover:bg-amber-600 transition-colors"
        title="Afficher la progression"
      >
        {isDownloading ? (
          <div className="relative">
            <Download className="w-5 h-5 animate-pulse" />
            <span className="absolute -top-1 -right-1 text-[9px] font-bold">
              {downloadProgress}%
            </span>
          </div>
        ) : modelLoaded ? (
          <CheckCircle className="w-5 h-5" />
        ) : (
          <AlertTriangle className="w-5 h-5" />
        )}
      </button>
    );
  }
  
  return (
    <div className="fixed bottom-20 md:bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-80 z-40">
      <div className={`rounded-lg shadow-lg border p-4 ${
        error 
          ? "bg-destructive/10 border-destructive/30" 
          : modelLoaded 
            ? "bg-green-500/10 border-green-500/30"
            : "bg-card border-border"
      }`}>
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {isDownloading ? (
              <Download className="w-4 h-4 text-amber-500 animate-pulse" />
            ) : modelLoaded ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : error ? (
              <AlertTriangle className="w-4 h-4 text-destructive" />
            ) : (
              <Cpu className="w-4 h-4 text-muted-foreground" />
            )}
            <span className="text-sm font-medium">
              {modelLoaded ? "Coach IA local" : "Téléchargement IA"}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button 
              onClick={() => setMinimized(true)}
              className="p-1 hover:bg-muted rounded"
              title="Réduire"
            >
              <span className="text-xs">—</span>
            </button>
            {isDownloading && (
              <button 
                onClick={cancelDownload}
                className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground"
                title="Annuler"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
        
        {/* Status */}
        <p className="text-xs text-muted-foreground mb-2">
          {downloadStatus || (modelLoaded ? "Prêt à l'emploi !" : "En attente...")}
        </p>
        
        {/* Progress */}
        {(isDownloading || downloadProgress > 0) && !modelLoaded && (
          <div className="space-y-1">
            <Progress value={downloadProgress} className="h-2" />
            <div className="flex items-center justify-between text-[10px] text-muted-foreground">
              <span>{downloadProgress}%</span>
              <span>~2.7 Go</span>
            </div>
          </div>
        )}
        
        {/* Error */}
        {error && (
          <div className="mt-2 text-xs text-destructive">
            {error}
            <button 
              onClick={() => window.location.reload()}
              className="ml-2 underline hover:no-underline"
            >
              Réessayer
            </button>
          </div>
        )}
        
        {/* Success */}
        {modelLoaded && (
          <div className="flex items-center gap-2 text-xs text-green-600">
            <Shield className="w-3.5 h-3.5" />
            <span>100% privé • Fonctionne offline</span>
          </div>
        )}
      </div>
    </div>
  );
};

// Combined export
const WebLLMBanners = () => {
  return (
    <>
      <WebLLMFirstTimeBanner />
      <WebLLMDownloadBanner />
    </>
  );
};

export default WebLLMBanners;
