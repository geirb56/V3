import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useWebLLM } from "@/context/WebLLMContext";
import { 
  MessageCircle, 
  Send, 
  Crown, 
  Loader2, 
  X, 
  Trash2,
  Sparkles,
  Download,
  Cpu,
  Wifi,
  Shield,
  CheckCircle
} from "lucide-react";
import { useLanguage } from "@/context/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// System prompt for WebLLM - Simplified for small models
const SYSTEM_PROMPT = `Tu es CardioCoach, un coach running français. Réponds en 2-3 phrases max. Sois positif et donne un conseil concret.`;

const ChatCoach = ({ isOpen, onClose, userId = "default" }) => {
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [subscriptionStatus, setSubscriptionStatus] = useState(null);
  const [checkingStatus, setCheckingStatus] = useState(true);
  const [trainingContext, setTrainingContext] = useState(null);
  
  // WebLLM from context
  const { 
    webGPUSupported, 
    modelLoaded, 
    modelCached,
    isDownloading,
    downloadProgress,
    downloadStatus,
    startDownload,
    loadFromCache,
    generateResponse,
    error: llmError
  } = useWebLLM();
  
  const messagesEndRef = useRef(null);

  // Check subscription and load data on open
  useEffect(() => {
    if (isOpen) {
      checkSubscription();
      loadHistory();
      loadTrainingContext();
      
      // Auto-load model from cache if available
      if (modelCached && !modelLoaded && !isDownloading) {
        loadFromCache();
      }
    }
  }, [isOpen, userId, modelCached, modelLoaded, isDownloading]);

  const checkSubscription = async () => {
    try {
      const res = await axios.get(`${API}/subscription/status?user_id=${userId}`);
      setSubscriptionStatus(res.data);
    } catch (err) {
      console.error("Error checking subscription:", err);
      setSubscriptionStatus({ tier: "free", messages_limit: 10, messages_remaining: 10 });
    } finally {
      setCheckingStatus(false);
    }
  };

  const loadTrainingContext = async () => {
    try {
      const res = await axios.get(`${API}/workouts?user_id=${userId}&limit=10`);
      const workouts = res.data || [];
      
      if (workouts.length > 0) {
        const totalKm = workouts.reduce((sum, w) => sum + (w.distance_km || 0), 0);
        const avgPaces = workouts.filter(w => w.avg_pace_min_km).map(w => w.avg_pace_min_km);
        const avgPace = avgPaces.length > 0 ? avgPaces.reduce((a, b) => a + b) / avgPaces.length : null;
        const avgCadences = workouts.filter(w => w.avg_cadence_spm).map(w => w.avg_cadence_spm);
        const avgCadence = avgCadences.length > 0 ? Math.round(avgCadences.reduce((a, b) => a + b) / avgCadences.length) : null;
        
        let zoneTotal = { z1: 0, z2: 0, z3: 0, z4: 0, z5: 0 };
        let zoneCount = 0;
        workouts.forEach(w => {
          if (w.effort_zone_distribution) {
            Object.keys(zoneTotal).forEach(z => {
              zoneTotal[z] += w.effort_zone_distribution[z] || 0;
            });
            zoneCount++;
          }
        });
        
        const zoneAvg = zoneCount > 0 
          ? Object.fromEntries(Object.entries(zoneTotal).map(([k, v]) => [k, Math.round(v / zoneCount)]))
          : null;
        
        setTrainingContext({
          nb_seances: workouts.length,
          km_total: Math.round(totalKm * 10) / 10,
          allure_moy: avgPace ? `${Math.floor(avgPace)}:${Math.round((avgPace % 1) * 60).toString().padStart(2, '0')}/km` : null,
          cadence_moy: avgCadence,
          zones: zoneAvg,
          derniere_seance: workouts[0]?.date ? new Date(workouts[0].date).toLocaleDateString('fr-FR') : null
        });
      }
    } catch (err) {
      console.error("Error loading training context:", err);
    }
  };

  const loadHistory = async () => {
    try {
      const res = await axios.get(`${API}/chat/history?user_id=${userId}&limit=30`);
      setMessages(res.data || []);
    } catch (err) {
      console.error("Error loading history:", err);
    }
  };

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Generate local response using WebLLM
  const generateLocalResponse = async (userMessage) => {
    // Simplified context for small models
    let contextStr = "";
    if (trainingContext && trainingContext.km_total) {
      contextStr = ` (${trainingContext.km_total}km cette semaine)`;
    }
    
    // Only keep last 2 messages for context (small model limitation)
    const recentMessages = messages.slice(-2).map(m => ({
      role: m.role,
      content: m.content.substring(0, 100) // Limit content length
    }));
    
    return await generateResponse([
      { role: "system", content: SYSTEM_PROMPT + contextStr },
      ...recentMessages,
      { role: "user", content: userMessage }
    ], { maxTokens: 100, temperature: 0.8, topP: 0.9, timeout: 20000 });
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setLoading(true);

    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: userMessage,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      let responseText = "";
      let usedLocalLLM = false;
      
      // Try WebLLM first if available (with timeout)
      if (modelLoaded) {
        try {
          console.log("Generating with WebLLM...");
          responseText = await generateLocalResponse(userMessage);
          usedLocalLLM = true;
          console.log("WebLLM response received");
        } catch (llmErr) {
          console.error("WebLLM generation error, falling back to server:", llmErr);
          // Will fallback to server response
        }
      }
      
      // Always send to backend (for message counting and fallback)
      const res = await axios.post(`${API}/chat/send`, {
        message: userMessage,
        user_id: userId,
        use_local_llm: usedLocalLLM
      });

      // Use server response if local failed or wasn't used
      if (!responseText) {
        responseText = res.data.response;
        console.log("Using server fallback response");
      } else {
        // Store local response on server for history
        try {
          await axios.post(`${API}/chat/store-response?user_id=${userId}&message_id=${res.data.message_id}&response=${encodeURIComponent(responseText)}`);
        } catch (storeErr) {
          console.error("Error storing response:", storeErr);
        }
      }

      const assistantMsg = {
        id: res.data.message_id,
        role: "assistant",
        content: responseText,
        timestamp: new Date().toISOString(),
        source: usedLocalLLM ? "local" : "server"
      };
      setMessages(prev => [...prev, assistantMsg]);

      setSubscriptionStatus(prev => ({
        ...prev,
        messages_remaining: res.data.messages_remaining,
        messages_used: (prev?.messages_used || 0) + 1
      }));

    } catch (err) {
      console.error("Error sending message:", err);
      const errorMsg = err.response?.data?.detail || "Erreur de connexion";
      
      const errorResponse = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `⚠️ ${errorMsg}`,
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorResponse]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearHistory = async () => {
    try {
      await axios.delete(`${API}/chat/history?user_id=${userId}`);
      setMessages([]);
    } catch (err) {
      console.error("Error clearing history:", err);
    }
  };

  if (!isOpen) return null;

  const canSendMessages = subscriptionStatus && subscriptionStatus.messages_remaining > 0;
  const tier = subscriptionStatus?.tier || "free";
  const tierName = subscriptionStatus?.tier_name || "Gratuit";
  const isUnlimited = subscriptionStatus?.is_unlimited || false;
  const isPremium = tier !== "free";

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm" data-testid="chat-overlay">
      <div className="fixed right-0 top-0 h-full w-full sm:w-[420px] bg-background border-l border-border shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-card">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <MessageCircle className="w-4 h-4 text-primary" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-semibold text-sm">Chat Coach</h2>
                {isPremium && (
                  <Badge className="text-[8px] bg-amber-500">{tierName}</Badge>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground">
                {isUnlimited 
                  ? "Illimité" 
                  : `${subscriptionStatus?.messages_remaining || 0}/${subscriptionStatus?.messages_limit || 10} messages`
                }
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* WebLLM status indicator */}
            <div 
              className="flex items-center gap-1 px-2 py-1 rounded-full bg-muted/50" 
              title={modelLoaded ? "IA locale active (100% privé)" : modelCached ? "Modèle en cache" : webGPUSupported ? "IA locale disponible" : "Mode serveur"}
            >
              {modelLoaded ? (
                <>
                  <Cpu className="w-3 h-3 text-green-500" />
                  <span className="text-[9px] text-green-500">Local</span>
                </>
              ) : modelCached ? (
                <>
                  <CheckCircle className="w-3 h-3 text-amber-500" />
                  <span className="text-[9px] text-amber-500">Prêt</span>
                </>
              ) : webGPUSupported ? (
                <>
                  <Cpu className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[9px] text-muted-foreground">GPU</span>
                </>
              ) : (
                <>
                  <Wifi className="w-3 h-3 text-amber-500" />
                  <span className="text-[9px] text-amber-500">Serveur</span>
                </>
              )}
            </div>
            {messages.length > 0 && (
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={clearHistory}
                className="h-8 w-8"
                title="Effacer l'historique"
              >
                <Trash2 className="w-4 h-4 text-muted-foreground" />
              </Button>
            )}
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={onClose}
              className="h-8 w-8"
              data-testid="close-chat"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Content */}
        {checkingStatus ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* WebLLM Download in Progress */}
            {isDownloading && (
              <div className="p-3 bg-amber-500/10 border-b border-amber-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <Download className="w-4 h-4 text-amber-500 animate-pulse" />
                  <span className="text-xs text-amber-600 font-medium">
                    {downloadStatus || "Téléchargement..."}
                  </span>
                </div>
                <Progress value={downloadProgress} className="h-1.5" />
                <p className="text-[10px] text-muted-foreground mt-1">
                  Tu peux continuer à utiliser l'app, le téléchargement continue en arrière-plan
                </p>
              </div>
            )}

            {/* WebLLM Init Button (if not loaded/downloading and premium) */}
            {!modelLoaded && !modelCached && !isDownloading && webGPUSupported && isPremium && !llmError && (
              <div className="p-3 bg-gradient-to-r from-amber-500/10 to-orange-500/10 border-b border-amber-500/20">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                      <p className="text-xs font-medium text-amber-600">Coach IA local disponible</p>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      ~600 Mo • Wi-Fi recommandé • 100% privé
                    </p>
                  </div>
                  <Button 
                    size="sm" 
                    onClick={startDownload}
                    className="text-xs h-7 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600"
                  >
                    <Download className="w-3 h-3 mr-1" />
                    Télécharger
                  </Button>
                </div>
              </div>
            )}

            {/* Model Cached - Load Button */}
            {modelCached && !modelLoaded && !isDownloading && (
              <div className="p-2 bg-green-500/10 border-b border-green-500/20">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                    <span className="text-[10px] text-green-600">
                      Modèle en cache • Prêt à charger
                    </span>
                  </div>
                  <Button 
                    size="sm" 
                    variant="ghost"
                    onClick={loadFromCache}
                    className="text-xs h-6 text-green-600 hover:text-green-700"
                  >
                    Charger
                  </Button>
                </div>
              </div>
            )}

            {/* Model Loaded Success */}
            {modelLoaded && (
              <div className="p-2 bg-green-500/10 border-b border-green-500/20">
                <div className="flex items-center gap-2">
                  <Shield className="w-3.5 h-3.5 text-green-500" />
                  <span className="text-[10px] text-green-600">
                    Coach IA local actif • 100% privé • Offline
                  </span>
                </div>
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="text-center text-muted-foreground text-sm py-8">
                  <MessageCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Pose ta première question !</p>
                  <p className="text-xs mt-1 text-muted-foreground/70">
                    Ex: "Comment je récupère ?" ou "Analyse ma semaine"
                  </p>
                  {!isPremium && webGPUSupported && (
                    <div className="mt-4 p-3 bg-muted/50 rounded-lg">
                      <p className="text-xs">
                        💡 Passe à un abonnement premium pour le coach IA local !
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground rounded-br-sm"
                          : msg.isError
                          ? "bg-destructive/10 text-destructive rounded-bl-sm"
                          : "bg-muted rounded-bl-sm"
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      {msg.source === "local" && (
                        <div className="flex items-center gap-1 mt-1 opacity-50">
                          <Cpu className="w-2.5 h-2.5" />
                          <span className="text-[9px]">Local</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-muted rounded-2xl rounded-bl-sm px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1">
                        <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                        <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                      {modelLoaded && (
                        <span className="text-[9px] text-muted-foreground ml-1">
                          Génération locale...
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-border bg-card">
              {!isUnlimited && subscriptionStatus?.messages_remaining <= 3 && subscriptionStatus?.messages_remaining > 0 && (
                <p className="text-xs text-amber-500 mb-2 text-center">
                  ⚠️ Plus que {subscriptionStatus.messages_remaining} messages ce mois
                </p>
              )}
              
              {!canSendMessages ? (
                <div className="text-center py-2">
                  <p className="text-xs text-destructive mb-2">
                    Tu as atteint ta limite de {subscriptionStatus?.messages_limit} messages ce mois-ci.
                  </p>
                  <Button 
                    size="sm" 
                    onClick={() => { onClose(); navigate("/subscription"); }}
                    className="bg-gradient-to-r from-amber-500 to-orange-500"
                  >
                    <Crown className="w-3.5 h-3.5 mr-1" />
                    Passer au niveau supérieur
                  </Button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Pose ta question..."
                    className="flex-1"
                    disabled={loading}
                    data-testid="chat-input"
                  />
                  <Button 
                    onClick={handleSend} 
                    disabled={loading || !input.trim()}
                    size="icon"
                    data-testid="send-btn"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ChatCoach;
