import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/context/LanguageContext";
import { Globe, Info, Link2, Loader2, Check, X, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const USER_ID = "default";

export default function Settings() {
  const { t, lang, setLang } = useLanguage();
  const [searchParams, setSearchParams] = useSearchParams();
  const [garminStatus, setGarminStatus] = useState(null);
  const [loadingGarmin, setLoadingGarmin] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    loadGarminStatus();
    
    // Handle OAuth callback
    const garminParam = searchParams.get("garmin");
    if (garminParam === "connected") {
      toast.success(lang === "fr" ? "Garmin connecte" : "Garmin connected");
      setSearchParams({});
      loadGarminStatus();
    } else if (garminParam === "error") {
      toast.error(lang === "fr" ? "Erreur de connexion" : "Connection failed");
      setSearchParams({});
    }
  }, [searchParams]);

  const loadGarminStatus = async () => {
    try {
      const res = await axios.get(`${API}/garmin/status?user_id=${USER_ID}`);
      setGarminStatus(res.data);
    } catch (error) {
      console.error("Failed to load Garmin status:", error);
      setGarminStatus({ connected: false, last_sync: null, workout_count: 0 });
    } finally {
      setLoadingGarmin(false);
    }
  };

  const handleConnectGarmin = async () => {
    setConnecting(true);
    try {
      const res = await axios.get(`${API}/garmin/authorize`);
      // Redirect to Garmin OAuth
      window.location.href = res.data.authorization_url;
    } catch (error) {
      console.error("Failed to initiate Garmin auth:", error);
      const message = error.response?.data?.detail || (lang === "fr" ? "Erreur de connexion" : "Connection failed");
      toast.error(message);
      setConnecting(false);
    }
  };

  const handleDisconnectGarmin = async () => {
    try {
      await axios.delete(`${API}/garmin/disconnect?user_id=${USER_ID}`);
      setGarminStatus({ connected: false, last_sync: null, workout_count: 0 });
      toast.success(lang === "fr" ? "Garmin deconnecte" : "Garmin disconnected");
    } catch (error) {
      console.error("Failed to disconnect Garmin:", error);
      toast.error(lang === "fr" ? "Erreur" : "Error");
    }
  };

  const handleSyncGarmin = async () => {
    setSyncing(true);
    try {
      const res = await axios.post(`${API}/garmin/sync?user_id=${USER_ID}`);
      if (res.data.success) {
        toast.success(res.data.message);
        loadGarminStatus();
      } else {
        toast.error(res.data.message);
      }
    } catch (error) {
      console.error("Failed to sync Garmin:", error);
      toast.error(lang === "fr" ? "Erreur de synchronisation" : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const formatLastSync = (isoString) => {
    if (!isoString) return lang === "fr" ? "Jamais" : "Never";
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (lang === "fr") {
      if (diffMins < 1) return "A l'instant";
      if (diffMins < 60) return `Il y a ${diffMins} min`;
      if (diffHours < 24) return `Il y a ${diffHours}h`;
      if (diffDays < 7) return `Il y a ${diffDays}j`;
      return date.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
    }
    
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString("en-US", { day: "numeric", month: "short" });
  };

  return (
    <div className="p-6 md:p-8 pb-24 md:pb-8" data-testid="settings-page">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-heading text-2xl md:text-3xl uppercase tracking-tight font-bold mb-1">
          {t("settings.title")}
        </h1>
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          {t("settings.subtitle")}
        </p>
      </div>

      <div className="space-y-6">
        {/* Data Sync Section */}
        <Card className="bg-card border-border">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 flex items-center justify-center bg-muted border border-border flex-shrink-0">
                <Link2 className="w-5 h-5 text-primary" />
              </div>
              <div className="flex-1">
                <h2 className="font-heading text-lg uppercase tracking-tight font-semibold mb-1">
                  {t("settings.dataSync")}
                </h2>
                <p className="font-mono text-xs text-muted-foreground mb-4">
                  {t("settings.dataSyncDesc")}
                </p>
                
                {loadingGarmin ? (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="font-mono text-xs">{t("common.loading")}</span>
                  </div>
                ) : garminStatus?.connected ? (
                  <div className="space-y-4">
                    {/* Connected Status */}
                    <div className="flex items-center gap-2 text-chart-2">
                      <Check className="w-4 h-4" />
                      <span className="font-mono text-xs uppercase tracking-wider">
                        {t("settings.connected")}
                      </span>
                    </div>
                    
                    {/* Last Sync Info */}
                    <div className="p-3 bg-muted/50 border border-border">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-1">
                            {t("settings.lastSync")}
                          </p>
                          <p className="font-mono text-sm">
                            {formatLastSync(garminStatus.last_sync)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-1">
                            {t("settings.workouts")}
                          </p>
                          <p className="font-mono text-sm">
                            {garminStatus.workout_count}
                          </p>
                        </div>
                      </div>
                    </div>
                    
                    {/* Actions */}
                    <div className="flex gap-3">
                      <Button
                        onClick={handleSyncGarmin}
                        disabled={syncing}
                        data-testid="sync-garmin"
                        className="bg-primary text-white hover:bg-primary/90 rounded-none uppercase font-bold tracking-wider text-xs h-9 px-4 flex items-center gap-2"
                      >
                        {syncing ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <RefreshCw className="w-4 h-4" />
                        )}
                        {t("settings.sync")}
                      </Button>
                      <Button
                        onClick={handleDisconnectGarmin}
                        variant="ghost"
                        data-testid="disconnect-garmin"
                        className="text-muted-foreground hover:text-destructive rounded-none uppercase font-mono text-xs h-9 px-4"
                      >
                        {t("settings.disconnect")}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <X className="w-4 h-4" />
                      <span className="font-mono text-xs uppercase tracking-wider">
                        {t("settings.notConnected")}
                      </span>
                    </div>
                    <Button
                      onClick={handleConnectGarmin}
                      disabled={connecting}
                      data-testid="connect-garmin"
                      className="bg-primary text-white hover:bg-primary/90 rounded-none uppercase font-bold tracking-wider text-xs h-9 px-4 flex items-center gap-2"
                    >
                      {connecting ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Link2 className="w-4 h-4" />
                      )}
                      {t("settings.connect")}
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Language Setting */}
        <Card className="bg-card border-border">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 flex items-center justify-center bg-muted border border-border flex-shrink-0">
                <Globe className="w-5 h-5 text-primary" />
              </div>
              <div className="flex-1">
                <h2 className="font-heading text-lg uppercase tracking-tight font-semibold mb-1">
                  {t("settings.language")}
                </h2>
                <p className="font-mono text-xs text-muted-foreground mb-4">
                  {t("settings.languageDesc")}
                </p>
                
                <div className="flex gap-3">
                  <button
                    onClick={() => setLang("en")}
                    data-testid="lang-en"
                    className={`flex-1 p-4 border font-mono text-sm uppercase tracking-wider transition-colors ${
                      lang === "en"
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border text-muted-foreground hover:border-primary/30 hover:text-foreground"
                    }`}
                  >
                    <span className="block text-lg mb-1">EN</span>
                    <span className="block text-xs">{t("settings.english")}</span>
                  </button>
                  
                  <button
                    onClick={() => setLang("fr")}
                    data-testid="lang-fr"
                    className={`flex-1 p-4 border font-mono text-sm uppercase tracking-wider transition-colors ${
                      lang === "fr"
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border text-muted-foreground hover:border-primary/30 hover:text-foreground"
                    }`}
                  >
                    <span className="block text-lg mb-1">FR</span>
                    <span className="block text-xs">{t("settings.french")}</span>
                  </button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* About */}
        <Card className="bg-card border-border">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 flex items-center justify-center bg-muted border border-border flex-shrink-0">
                <Info className="w-5 h-5 text-muted-foreground" />
              </div>
              <div className="flex-1">
                <h2 className="font-heading text-lg uppercase tracking-tight font-semibold mb-1">
                  {t("settings.about")}
                </h2>
                <p className="font-mono text-xs text-muted-foreground mb-4">
                  {t("settings.aboutDesc")}
                </p>
                <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  {t("settings.version")} 1.1.0
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
