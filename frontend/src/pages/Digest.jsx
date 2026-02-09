import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/context/LanguageContext";
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Activity, 
  Flame,
  Target,
  Calendar,
  MessageCircle,
  Loader2,
  RefreshCw,
  CheckCircle2,
  History,
  Flag
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const USER_ID = "default";

// CARTE 2 - Signal Card Component
function SignalCard({ signal, t }) {
  const getIcon = () => {
    if (signal.key === "load") {
      if (signal.status === "up") return <TrendingUp className="w-5 h-5" />;
      if (signal.status === "down") return <TrendingDown className="w-5 h-5" />;
      return <Minus className="w-5 h-5" />;
    }
    if (signal.key === "intensity") {
      if (signal.status === "hard") return <Flame className="w-5 h-5" />;
      if (signal.status === "easy") return <Activity className="w-5 h-5" />;
      return <Target className="w-5 h-5" />;
    }
    return <Calendar className="w-5 h-5" />;
  };

  const getColor = () => {
    if (signal.key === "load") {
      if (signal.status === "up") return "text-orange-400";
      if (signal.status === "down") return "text-blue-400";
      return "text-emerald-400";
    }
    if (signal.key === "intensity") {
      if (signal.status === "hard") return "text-orange-400";
      if (signal.status === "easy") return "text-emerald-400";
      return "text-primary";
    }
    // Regularity
    if (signal.status === "high") return "text-emerald-400";
    if (signal.status === "moderate") return "text-amber-400";
    return "text-red-400";
  };

  const getLabel = () => {
    if (signal.key === "load") {
      return t(`digest.load.${signal.status}`);
    }
    if (signal.key === "intensity") {
      return t(`digest.intensity.${signal.status}`);
    }
    return t(`digest.regularity.${signal.status}`);
  };

  return (
    <div className="flex flex-col items-center p-3 bg-muted/30 rounded-lg">
      <div className={`mb-2 ${getColor()}`}>
        {getIcon()}
      </div>
      <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground mb-1">
        {t(`digest.signals.${signal.key}`)}
      </p>
      <p className={`font-mono text-xs font-semibold ${getColor()}`}>
        {signal.value || getLabel()}
      </p>
    </div>
  );
}

export default function Digest() {
  const { t, lang } = useLanguage();
  const navigate = useNavigate();
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadReview();
  }, [lang]);

  const loadReview = async (forceRefresh = false) => {
    if (forceRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    
    try {
      const res = await axios.get(`${API}/coach/digest?user_id=${USER_ID}&language=${lang}`);
      setReview(res.data);
    } catch (error) {
      console.error("Failed to load review:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const formatDateRange = () => {
    if (!review) return "";
    const start = new Date(review.period_start);
    const end = new Date(review.period_end);
    const locale = lang === "fr" ? "fr-FR" : "en-US";
    const opts = { month: "short", day: "numeric" };
    return `${start.toLocaleDateString(locale, opts)} - ${end.toLocaleDateString(locale, opts)}`;
  };

  const formatHours = (minutes) => {
    if (!minutes) return "0";
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours === 0) return `${mins}min`;
    if (mins === 0) return `${hours}h`;
    return `${hours}h${mins}`;
  };

  const calculateDaysUntil = (dateStr) => {
    if (!dateStr) return null;
    const eventDate = new Date(dateStr);
    const today = new Date();
    const diffTime = eventDate - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays > 0 ? diffDays : null;
  };

  if (loading) {
    return (
      <div className="p-6 md:p-8 pb-24 md:pb-8 flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            {t("digest.generating")}
          </span>
        </div>
      </div>
    );
  }

  const metrics = review?.metrics || {};
  const comparison = review?.comparison || {};
  const signals = review?.signals || [];
  const recommendations = review?.recommendations || [];
  const recommendationsFollowup = review?.recommendations_followup;
  const userGoal = review?.user_goal;
  const daysUntil = userGoal ? calculateDaysUntil(userGoal.event_date) : null;

  return (
    <div className="p-4 md:p-8 pb-24 md:pb-8 max-w-lg mx-auto" data-testid="digest-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-heading text-xl md:text-2xl uppercase tracking-tight font-bold mb-0.5">
            {t("digest.title")}
          </h1>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            {formatDateRange()}
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => loadReview(true)}
          disabled={refreshing}
          data-testid="refresh-review"
          className="text-muted-foreground hover:text-foreground"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {/* User Goal Context - if exists */}
      {userGoal && daysUntil && (
        <Card className="bg-amber-500/5 border-amber-500/20 mb-4">
          <CardContent className="p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Flag className="w-4 h-4 text-amber-400 flex-shrink-0" />
                <div>
                  <p className="font-mono text-xs text-amber-400 font-semibold">
                    {userGoal.event_name}
                  </p>
                  <p className="font-mono text-[10px] text-muted-foreground">
                    {userGoal.distance_km}km • {daysUntil} {lang === "fr" ? "jours" : "days"}
                  </p>
                </div>
              </div>
              {userGoal.target_pace && (
                <div className="text-right">
                  <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
                    {t("settings.targetPace")}
                  </p>
                  <p className="font-mono text-sm font-bold text-amber-400">
                    {userGoal.target_pace}/km
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* CARTE 1 - Synthèse du Coach */}
      <Card className="bg-card border-border mb-4">
        <CardContent className="p-4">
          <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground mb-2">
            {t("digest.coachSummary")}
          </p>
          <p className="font-mono text-sm md:text-base leading-relaxed" data-testid="coach-summary">
            {review?.coach_summary || t("digest.noData")}
          </p>
        </CardContent>
      </Card>

      {/* CARTE 2 - Signaux Clés */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {signals.map((signal) => (
          <SignalCard 
            key={signal.key}
            signal={signal}
            t={t}
          />
        ))}
      </div>

      {/* CARTE 3 - Chiffres Essentiels */}
      <Card className="bg-card border-border mb-4">
        <CardContent className="p-4">
          <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground mb-3">
            {t("digest.essentialNumbers")}
          </p>
          <div className="flex items-center justify-between divide-x divide-border">
            <div className="flex-1 text-center pr-3">
              <p className="font-mono text-2xl font-bold text-foreground">
                {metrics.total_sessions || 0}
              </p>
              <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
                {t("digest.sessions")}
              </p>
            </div>
            <div className="flex-1 text-center px-3">
              <p className="font-mono text-2xl font-bold text-foreground">
                {metrics.total_distance_km || 0}
              </p>
              <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
                {t("digest.km")}
              </p>
            </div>
            <div className="flex-1 text-center pl-3">
              <p className="font-mono text-2xl font-bold text-foreground">
                {formatHours(metrics.total_duration_min)}
              </p>
              <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
                {t("digest.hours")}
              </p>
            </div>
          </div>
          {/* Comparison vs last week */}
          {comparison.distance_diff_pct !== undefined && comparison.distance_diff_pct !== 0 && (
            <div className="mt-3 pt-3 border-t border-border">
              <p className={`font-mono text-xs text-center ${
                comparison.distance_diff_pct > 0 ? "text-orange-400" : "text-blue-400"
              }`}>
                {comparison.distance_diff_pct > 0 ? "+" : ""}{comparison.distance_diff_pct}% {t("digest.vsLastWeek")}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recommendations Followup - Last week's advice */}
      {recommendationsFollowup && (
        <Card className="bg-muted/30 border-border mb-4">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <History className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground mb-1">
                  {t("digest.recommendationsFollowup")}
                </p>
                <p className="font-mono text-xs text-muted-foreground leading-relaxed" data-testid="recommendations-followup">
                  {recommendationsFollowup}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* CARTE 4 - Lecture du Coach */}
      {review?.coach_reading && (
        <Card className="bg-card border-border mb-4">
          <CardContent className="p-4">
            <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground mb-2">
              {t("digest.coachReading")}
            </p>
            <p className="font-mono text-sm leading-relaxed text-muted-foreground" data-testid="coach-reading">
              {review.coach_reading}
            </p>
          </CardContent>
        </Card>
      )}

      {/* CARTE 5 - Préconisations du Coach (OBLIGATOIRE) */}
      {recommendations.length > 0 && (
        <Card className="bg-primary/5 border-primary/20 mb-4">
          <CardContent className="p-4">
            <p className="font-mono text-[9px] uppercase tracking-widest text-primary mb-3">
              {t("digest.recommendations")}
            </p>
            <div className="space-y-2">
              {recommendations.map((rec, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 mt-0.5 text-primary flex-shrink-0" />
                  <p className="font-mono text-sm text-foreground leading-relaxed">
                    {rec}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* CARTE 6 - Question au Coach (Optionnel) */}
      <Button
        onClick={() => navigate("/coach")}
        variant="ghost"
        data-testid="ask-coach-btn"
        className="w-full bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/50 rounded-lg h-12 font-mono text-xs uppercase tracking-wider flex items-center justify-center gap-2"
      >
        <MessageCircle className="w-4 h-4" />
        <span>{t("digest.askCoach")}</span>
      </Button>
    </div>
  );
}
