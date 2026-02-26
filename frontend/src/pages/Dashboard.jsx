import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { Card, CardContent } from "@/components/ui/card";
import { useLanguage } from "@/context/LanguageContext";
import { 
  Activity, 
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronRight,
  Bike,
  Footprints,
  Loader2,
  Lightbulb,
  Scale,
  Battery,
  BatteryLow,
  BatteryMedium,
  BatteryFull,
  Sparkles,
  Target,
  AlertTriangle
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const getWorkoutIcon = (type) => {
  if (type === "cycle") return Bike;
  return Footprints;
};

const formatDuration = (minutes) => {
  if (!minutes) return "--";
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hrs > 0) return `${hrs}h${mins > 0 ? mins : ""}`;
  return `${mins}m`;
};

// Recovery Score Gauge Component
function RecoveryGauge({ score, status, phrase }) {
  const getColor = () => {
    if (status === "ready") return "text-emerald-400";
    if (status === "moderate") return "text-amber-400";
    return "text-red-400";
  };

  const getBgColor = () => {
    if (status === "ready") return "bg-emerald-400/10";
    if (status === "moderate") return "bg-amber-400/10";
    return "bg-red-400/10";
  };

  const getIcon = () => {
    if (status === "ready") return BatteryFull;
    if (status === "moderate") return BatteryMedium;
    return BatteryLow;
  };

  const Icon = getIcon();
  const circumference = 2 * Math.PI * 36;
  const progress = (score / 100) * circumference;

  return (
    <Card className={`border-border ${getBgColor()}`}>
      <CardContent className="p-4">
        <div className="flex items-center gap-4">
          {/* Circular Gauge */}
          <div className="relative w-20 h-20 flex-shrink-0">
            <svg className="w-20 h-20 transform -rotate-90" viewBox="0 0 80 80">
              {/* Background circle */}
              <circle
                cx="40"
                cy="40"
                r="36"
                fill="none"
                stroke="currentColor"
                strokeWidth="6"
                className="text-muted/30"
              />
              {/* Progress circle */}
              <circle
                cx="40"
                cy="40"
                r="36"
                fill="none"
                stroke="currentColor"
                strokeWidth="6"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={circumference - progress}
                className={getColor()}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={`font-mono text-xl font-bold ${getColor()}`}>
                {score}
              </span>
            </div>
          </div>

          {/* Text */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Icon className={`w-4 h-4 ${getColor()}`} />
              <span className={`font-mono text-xs uppercase tracking-wider font-semibold ${getColor()}`}>
                {status === "ready" ? "Ready" : status === "moderate" ? "Moderate" : "Low"}
              </span>
            </div>
            <p className="font-mono text-xs text-muted-foreground leading-relaxed">
              {phrase}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const [insight, setInsight] = useState(null);
  const [workouts, setWorkouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const { t, lang } = useLanguage();
  const fetchedRef = useRef(false);
  const lastLangRef = useRef(lang);

  useEffect(() => {
    // Prevent double fetch on mount (React StrictMode)
    // Only refetch if language changed
    if (fetchedRef.current && lastLangRef.current === lang) {
      return;
    }
    
    fetchedRef.current = true;
    lastLangRef.current = lang;
    fetchData();
  }, [lang]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [insightRes, workoutsRes, ragRes] = await Promise.all([
        axios.get(`${API}/dashboard/insight?language=${lang}`),
        axios.get(`${API}/workouts`),
        axios.get(`${API}/rag/dashboard`).catch(() => ({ data: null }))
      ]);
      setInsight(insightRes.data);
      setWorkouts(workoutsRes.data);
      // Merge RAG data into insight for enhanced display
      if (ragRes.data) {
        setInsight(prev => ({
          ...prev,
          rag: ragRes.data
        }));
      }
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setLoading(false);
    }
  };

  const getLoadColor = (signal) => {
    if (signal === "high") return "text-chart-1";
    if (signal === "low") return "text-chart-4";
    return "text-chart-2";
  };

  const getTrendIcon = (trend) => {
    if (trend === "up") return TrendingUp;
    if (trend === "down") return TrendingDown;
    return Minus;
  };

  const getTrendColor = (trend) => {
    if (trend === "up") return "text-chart-2";
    if (trend === "down") return "text-chart-4";
    return "text-muted-foreground";
  };

  if (loading) {
    return (
      <div className="p-4 pb-24 flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  const TrendIcon = insight?.month ? getTrendIcon(insight.month.trend) : Minus;
  const recovery = insight?.recovery_score;
  const rag = insight?.rag;

  return (
    <div className="p-4 pb-24" data-testid="dashboard">
      {/* 1) COACH INSIGHT - TOP PRIORITY */}
      {insight?.coach_insight && (
        <Card className="coach-insight-card bg-primary/5 border-primary/20 mb-4 animate-in">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                <Lightbulb className="w-4 h-4 text-primary" />
              </div>
              <div className="flex-1">
                <p className="font-mono text-[9px] uppercase tracking-widest text-primary/60 mb-1">
                  {lang === "fr" ? "Conseil du coach" : "Coach Insight"}
                </p>
                <p className="font-mono text-sm text-primary leading-relaxed" data-testid="coach-insight">
                  {insight.coach_insight}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* RAG ENRICHED SUMMARY - NEW */}
      {rag?.rag_summary && (
        <Card className="bg-card border-border mb-4" data-testid="rag-summary-card">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
                {lang === "fr" ? "Analyse personnalisée" : "Personalized Analysis"}
              </p>
            </div>
            <p className="font-mono text-xs text-muted-foreground leading-relaxed whitespace-pre-line" data-testid="rag-summary">
              {rag.rag_summary.split('\n').slice(0, 4).join('\n')}
            </p>
            
            {/* Points forts & améliorer */}
            {(rag.points_forts?.length > 0 || rag.points_ameliorer?.length > 0) && (
              <div className="mt-3 pt-3 border-t border-border flex flex-wrap gap-2">
                {rag.points_forts?.slice(0, 2).map((point, i) => (
                  <span key={`fort-${i}`} className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-500/10 text-emerald-400 rounded-sm">
                    <Target className="w-3 h-3" />
                    <span className="font-mono text-[10px]">{point}</span>
                  </span>
                ))}
                {rag.points_ameliorer?.slice(0, 1).map((point, i) => (
                  <span key={`ameliorer-${i}`} className="inline-flex items-center gap-1 px-2 py-1 bg-amber-500/10 text-amber-400 rounded-sm">
                    <AlertTriangle className="w-3 h-3" />
                    <span className="font-mono text-[10px]">{point}</span>
                  </span>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 2) RECOVERY SCORE - NEW */}
      {recovery && (
        <div className="mb-4">
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
            {t("dashboard.recovery")}
          </p>
          <RecoveryGauge 
            score={recovery.score} 
            status={recovery.status} 
            phrase={recovery.phrase}
          />
        </div>
      )}

      {/* 3) CURRENT WEEK - VOLUME FOCUS */}
      <div className="mb-4">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
          {t("dashboard.thisWeek")}
        </p>
        <div className="grid grid-cols-3 gap-2">
          {/* Sessions */}
          <Card className="bg-card border-border">
            <CardContent className="p-3 text-center">
              <Activity className="w-4 h-4 text-muted-foreground mx-auto mb-1" />
              <p className="font-mono text-xl font-bold">{insight?.week?.sessions || 0}</p>
              <p className="font-mono text-[9px] uppercase text-muted-foreground">
                {t("dashboard.sessions")}
              </p>
            </CardContent>
          </Card>

          {/* Volume */}
          <Card className="bg-card border-border">
            <CardContent className="p-3 text-center">
              <Scale className="w-4 h-4 text-muted-foreground mx-auto mb-1" />
              <p className="font-mono text-xl font-bold">{insight?.week?.volume_km || 0}</p>
              <p className="font-mono text-[9px] uppercase text-muted-foreground">
                {t("dashboard.km")}
              </p>
            </CardContent>
          </Card>

          {/* Load Signal */}
          <Card className="bg-card border-border">
            <CardContent className="p-3 text-center">
              <TrendingUp className={`w-4 h-4 mx-auto mb-1 ${getLoadColor(insight?.week?.load_signal)}`} />
              <p className={`font-mono text-xs font-bold ${getLoadColor(insight?.week?.load_signal)}`}>
                {t(`dashboard.load.${insight?.week?.load_signal || "balanced"}`)}
              </p>
              <p className="font-mono text-[9px] uppercase text-muted-foreground">
                {t("dashboard.load.label")}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 4) LAST MONTH - CONTEXT ONLY */}
      <div className="mb-4">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
          {t("dashboard.lastMonth")}
        </p>
        <Card className="bg-card border-border">
          <CardContent className="p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div>
                  <p className="font-mono text-lg font-bold">{insight?.month?.volume_km || 0}</p>
                  <p className="font-mono text-[9px] uppercase text-muted-foreground">{t("dashboard.km")}</p>
                </div>
                <div className="h-8 w-px bg-border" />
                <div>
                  <p className="font-mono text-lg font-bold">{insight?.month?.active_weeks || 0}</p>
                  <p className="font-mono text-[9px] uppercase text-muted-foreground">{t("dashboard.activeWeeks")}</p>
                </div>
              </div>
              <div className={`flex items-center gap-1 ${getTrendColor(insight?.month?.trend)}`}>
                <TrendIcon className="w-4 h-4" />
                <span className="font-mono text-xs uppercase">
                  {t(`dashboard.trend.${insight?.month?.trend || "stable"}`)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* RECENT WORKOUTS */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            {t("dashboard.recentWorkouts")}
          </p>
          <Link 
            to="/progress" 
            data-testid="view-all-workouts"
            className="font-mono text-[10px] uppercase text-primary hover:text-primary/80 flex items-center gap-1"
          >
            {t("dashboard.viewAll")} <ChevronRight className="w-3 h-3" />
          </Link>
        </div>

        <div className="space-y-2">
          {workouts.slice(0, 4).map((workout) => {
            const Icon = getWorkoutIcon(workout.type);
            const dateStr = new Date(workout.date).toLocaleDateString(
              lang === "fr" ? "fr-FR" : "en-US",
              { month: "short", day: "numeric" }
            );
            
            return (
              <Link
                key={workout.id}
                to={`/workout/${workout.id}`}
                data-testid={`workout-card-${workout.id}`}
                className="block"
              >
                <Card className="bg-card border-border hover:border-primary/30 transition-colors">
                  <CardContent className="p-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 flex items-center justify-center bg-muted border border-border flex-shrink-0">
                        <Icon className="w-4 h-4 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-mono text-xs font-medium truncate">{workout.name}</p>
                        <p className="font-mono text-[10px] text-muted-foreground">{dateStr}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-mono text-xs font-medium">{workout.distance_km?.toFixed(1)} km</p>
                        <p className="font-mono text-[10px] text-muted-foreground">
                          {formatDuration(workout.duration_minutes)}
                        </p>
                      </div>
                      <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
