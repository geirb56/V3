import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/context/LanguageContext";
import { 
  ArrowLeft, 
  Heart, 
  TrendingUp,
  TrendingDown,
  Minus,
  Zap,
  Scale,
  Activity,
  MessageSquare,
  Loader2,
  Bike,
  Footprints,
  HeartPulse
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

// Heart Rate Zones Visualization Component
const HRZonesChart = ({ zones, t }) => {
  if (!zones) return null;
  
  // Zone configuration with colors and labels
  const zoneConfig = [
    { key: "z1", color: "#3B82F6", label: "Z1", desc: "recovery" },
    { key: "z2", color: "#22C55E", label: "Z2", desc: "endurance" },
    { key: "z3", color: "#EAB308", label: "Z3", desc: "tempo" },
    { key: "z4", color: "#F97316", label: "Z4", desc: "threshold" },
    { key: "z5", color: "#EF4444", label: "Z5", desc: "max" },
  ];
  
  // Find max percentage for scaling
  const maxPct = Math.max(...zoneConfig.map(z => zones[z.key] || 0), 1);
  
  return (
    <div className="space-y-2">
      {zoneConfig.map((zone) => {
        const pct = zones[zone.key] || 0;
        const barWidth = Math.max((pct / maxPct) * 100, pct > 0 ? 8 : 0);
        
        return (
          <div key={zone.key} className="flex items-center gap-2">
            <span className="font-mono text-[10px] w-6 text-muted-foreground">
              {zone.label}
            </span>
            <div className="flex-1 h-5 bg-muted/30 relative overflow-hidden">
              <div 
                className="h-full transition-all duration-500 ease-out flex items-center"
                style={{ 
                  width: `${barWidth}%`,
                  backgroundColor: zone.color,
                  minWidth: pct > 0 ? "24px" : "0"
                }}
              >
                {pct > 0 && (
                  <span className="font-mono text-[10px] text-white font-semibold px-1.5 drop-shadow-sm">
                    {pct}%
                  </span>
                )}
              </div>
            </div>
            <span className="font-mono text-[9px] w-16 text-muted-foreground hidden sm:block">
              {t(`zones.${zone.desc}`)}
            </span>
          </div>
        );
      })}
    </div>
  );
};

// Zone summary component
const ZoneSummary = ({ zones, t }) => {
  if (!zones) return null;
  
  const easyPct = (zones.z1 || 0) + (zones.z2 || 0);
  const moderatePct = zones.z3 || 0;
  const hardPct = (zones.z4 || 0) + (zones.z5 || 0);
  
  // Determine dominant zone type
  let dominant = "balanced";
  let dominantColor = "text-chart-3";
  
  if (hardPct >= 50) {
    dominant = "hard";
    dominantColor = "text-chart-1";
  } else if (easyPct >= 60) {
    dominant = "easy";
    dominantColor = "text-chart-2";
  }
  
  return (
    <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
      <div className="flex gap-4">
        <div className="text-center">
          <p className="font-mono text-xs font-semibold text-chart-2">{easyPct}%</p>
          <p className="font-mono text-[8px] text-muted-foreground uppercase">{t("zones.easy")}</p>
        </div>
        <div className="text-center">
          <p className="font-mono text-xs font-semibold text-chart-3">{moderatePct}%</p>
          <p className="font-mono text-[8px] text-muted-foreground uppercase">{t("zones.moderate")}</p>
        </div>
        <div className="text-center">
          <p className="font-mono text-xs font-semibold text-chart-1">{hardPct}%</p>
          <p className="font-mono text-[8px] text-muted-foreground uppercase">{t("zones.hard")}</p>
        </div>
      </div>
      <div className={`px-2 py-1 rounded-sm ${dominant === "hard" ? "bg-chart-1/10" : dominant === "easy" ? "bg-chart-2/10" : "bg-chart-3/10"}`}>
        <p className={`font-mono text-[10px] font-semibold ${dominantColor}`}>
          {t(`zones.dominant_${dominant}`)}
        </p>
      </div>
    </div>
  );
};

export default function WorkoutDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { t, lang } = useLanguage();
  const [workout, setWorkout] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWorkout();
  }, [id, lang]);

  const loadWorkout = async () => {
    setLoading(true);
    try {
      const [workoutRes, analysisRes] = await Promise.all([
        axios.get(`${API}/workouts/${id}`),
        axios.get(`${API}/coach/workout-analysis/${id}?language=${lang}`)
      ]);
      setWorkout(workoutRes.data);
      setAnalysis(analysisRes.data);
    } catch (error) {
      console.error("Failed to load workout:", error);
      try {
        const res = await axios.get(`${API}/workouts/${id}`);
        setWorkout(res.data);
      } catch (e) {
        console.error("Workout not found");
      }
    } finally {
      setLoading(false);
    }
  };

  const goToDeepAnalysis = () => {
    navigate(`/workout/${id}/analysis`);
  };

  const goToAskCoach = () => {
    navigate("/coach");
  };

  if (loading) {
    return (
      <div className="p-4 pb-24 flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  if (!workout) {
    return (
      <div className="p-4 pb-24" data-testid="workout-not-found">
        <Link to="/" className="inline-flex items-center gap-2 text-muted-foreground mb-6">
          <ArrowLeft className="w-4 h-4" />
          <span className="font-mono text-xs uppercase">{t("workout.back")}</span>
        </Link>
        <p className="text-muted-foreground">{t("workout.notFound")}</p>
      </div>
    );
  }

  const Icon = getWorkoutIcon(workout.type);
  const typeLabel = t(`workoutTypes.${workout.type}`) || workout.type;
  const dateStr = new Date(workout.date).toLocaleDateString(
    lang === "fr" ? "fr-FR" : "en-US",
    { weekday: "short", month: "short", day: "numeric" }
  );

  // Session type styling
  const getSessionTypeStyle = (label) => {
    if (label === "hard") return "text-chart-1 bg-chart-1/10";
    if (label === "easy") return "text-chart-2 bg-chart-2/10";
    return "text-chart-3 bg-chart-3/10";
  };

  return (
    <div className="p-4 pb-24" data-testid="workout-detail">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <Link to="/" className="text-muted-foreground hover:text-foreground">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-muted-foreground" />
          <span className="font-mono text-[10px] uppercase text-muted-foreground">{typeLabel}</span>
        </div>
        <span className="font-mono text-[10px] text-muted-foreground">{dateStr}</span>
      </div>

      {/* Workout Title */}
      <h1 className="font-heading text-base uppercase tracking-tight font-bold mb-4 leading-tight">
        {workout.name}
      </h1>

      {/* 1) Coach Summary - Top */}
      {analysis?.coach_summary && (
        <Card className="bg-card border-border mb-3">
          <CardContent className="p-3">
            <p className="font-mono text-sm leading-relaxed" data-testid="coach-summary">
              {analysis.coach_summary}
            </p>
          </CardContent>
        </Card>
      )}

      {/* 2) Session Snapshot - 3 Cards */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        {/* Card A - Intensity */}
        {analysis?.intensity && (
          <Card className="bg-card border-border">
            <CardContent className="p-2">
              <div className="flex items-center gap-1 mb-1">
                <Zap className="w-3 h-3 text-muted-foreground" />
                <span className="font-mono text-[8px] uppercase tracking-widest text-muted-foreground">
                  {t("analysis.intensity")}
                </span>
              </div>
              <p className="font-mono text-xs font-semibold leading-tight">
                {analysis.intensity.pace || "--"}
              </p>
              {analysis.intensity.avg_hr && (
                <p className="font-mono text-[10px] text-muted-foreground flex items-center gap-1">
                  <Heart className="w-2.5 h-2.5" />
                  {analysis.intensity.avg_hr}
                </p>
              )}
              {analysis.intensity.label !== "normal" && (
                <p className={`font-mono text-[9px] mt-1 ${
                  analysis.intensity.label === "above_usual" ? "text-chart-1" : "text-chart-2"
                }`}>
                  {t(`analysis.labels.${analysis.intensity.label}`)}
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Card B - Load */}
        {analysis?.load && (
          <Card className="bg-card border-border">
            <CardContent className="p-2">
              <div className="flex items-center gap-1 mb-1">
                <Scale className="w-3 h-3 text-muted-foreground" />
                <span className="font-mono text-[8px] uppercase tracking-widest text-muted-foreground">
                  {t("analysis.load")}
                </span>
              </div>
              <p className="font-mono text-xs font-semibold leading-tight">
                {analysis.load.distance_km} km
              </p>
              <p className="font-mono text-[10px] text-muted-foreground">
                {formatDuration(analysis.load.duration_min)}
              </p>
              {analysis.load.direction !== "stable" && (
                <p className={`font-mono text-[9px] mt-1 flex items-center gap-0.5 ${
                  analysis.load.direction === "up" ? "text-chart-1" : "text-chart-4"
                }`}>
                  {analysis.load.direction === "up" ? (
                    <TrendingUp className="w-2.5 h-2.5" />
                  ) : (
                    <TrendingDown className="w-2.5 h-2.5" />
                  )}
                  {t(`analysis.load_${analysis.load.direction}`)}
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Card C - Type */}
        {analysis?.session_type && (
          <Card className="bg-card border-border">
            <CardContent className="p-2">
              <div className="flex items-center gap-1 mb-1">
                <Activity className="w-3 h-3 text-muted-foreground" />
                <span className="font-mono text-[8px] uppercase tracking-widest text-muted-foreground">
                  {t("analysis.type")}
                </span>
              </div>
              <div className={`inline-block px-2 py-1 rounded-sm ${getSessionTypeStyle(analysis.session_type.label)}`}>
                <p className="font-mono text-xs font-semibold">
                  {t(`analysis.session_types.${analysis.session_type.label}`)}
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* 3) Coach Insight */}
      {analysis?.insight && (
        <Card className="bg-card border-border mb-3">
          <CardContent className="p-3">
            <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground mb-1.5">
              {t("analysis.coachInsight")}
            </p>
            <p className="font-mono text-xs text-muted-foreground leading-relaxed" data-testid="coach-insight">
              {analysis.insight}
            </p>
          </CardContent>
        </Card>
      )}

      {/* 4) Guidance (Optional) */}
      {analysis?.guidance && (
        <Card className="bg-primary/5 border-primary/20 mb-3">
          <CardContent className="p-3">
            <p className="font-mono text-xs text-primary leading-relaxed" data-testid="guidance">
              {analysis.guidance}
            </p>
          </CardContent>
        </Card>
      )}

      {/* 5) Actions */}
      <div className="space-y-2 mt-4">
        <Button
          onClick={goToDeepAnalysis}
          data-testid="deep-analysis-btn"
          className="w-full bg-primary text-white hover:bg-primary/90 rounded-none h-10 font-mono text-xs uppercase tracking-wider flex items-center justify-center gap-2"
        >
          <MessageSquare className="w-3.5 h-3.5" />
          {t("analysis.viewDetailedAnalysis")}
        </Button>
        <Button
          onClick={goToAskCoach}
          variant="ghost"
          data-testid="ask-coach-btn"
          className="w-full text-muted-foreground hover:text-foreground rounded-none h-9 font-mono text-[11px] uppercase tracking-wider"
        >
          {t("analysis.askCoach")}
        </Button>
      </div>
    </div>
  );
}
