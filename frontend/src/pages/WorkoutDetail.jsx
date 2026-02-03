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
  GitCompare,
  MessageSquare,
  Loader2,
  Bike,
  Footprints
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

export default function WorkoutDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { t, lang } = useLanguage();
  const [workout, setWorkout] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    loadWorkout();
  }, [id]);

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
      // Try just the workout if analysis fails
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

  const refreshAnalysis = async () => {
    setAnalyzing(true);
    try {
      const res = await axios.get(`${API}/coach/workout-analysis/${id}?language=${lang}`);
      setAnalysis(res.data);
    } catch (error) {
      console.error("Analysis failed:", error);
    } finally {
      setAnalyzing(false);
    }
  };

  const goToDeepAnalysis = () => {
    navigate(`/coach?analyze=${id}`);
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

  return (
    <div className="p-4 pb-24" data-testid="workout-detail">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <Link to="/" className="text-muted-foreground hover:text-foreground">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-muted-foreground" />
          <span className="font-mono text-xs uppercase text-muted-foreground">{typeLabel}</span>
        </div>
        <span className="font-mono text-xs text-muted-foreground">{dateStr}</span>
      </div>

      {/* Workout Title */}
      <h1 className="font-heading text-lg uppercase tracking-tight font-bold mb-4 leading-tight">
        {workout.name}
      </h1>

      {/* Coach Summary */}
      {analysis?.coach_summary && (
        <Card className="bg-card border-border mb-4">
          <CardContent className="p-4">
            <p className="font-mono text-sm leading-relaxed" data-testid="coach-summary">
              {analysis.coach_summary}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Signal Cards */}
      <div className="grid grid-cols-1 gap-3 mb-4">
        {/* Intensity Card */}
        {analysis?.intensity && (
          <SignalCard
            icon={Zap}
            title={t("analysis.intensity")}
            items={[
              { label: workout.type === "run" ? t("analysis.pace") : t("analysis.speed"), value: analysis.intensity.pace },
              { label: t("analysis.avgHr"), value: analysis.intensity.avg_hr ? `${analysis.intensity.avg_hr} bpm` : null },
            ]}
            badge={analysis.intensity.label !== "normal" ? t(`analysis.labels.${analysis.intensity.label}`) : null}
            badgeColor={analysis.intensity.label === "above_usual" ? "text-chart-1" : "text-chart-2"}
          />
        )}

        {/* Load Card */}
        {analysis?.load && (
          <SignalCard
            icon={Scale}
            title={t("analysis.load")}
            items={[
              { label: t("dashboard.distance"), value: `${analysis.load.distance_km} km` },
              { label: t("dashboard.duration"), value: formatDuration(analysis.load.duration_min) },
            ]}
            badge={analysis.load.vs_baseline_pct !== 0 ? (
              <span className="flex items-center gap-1">
                {analysis.load.direction === "up" && <TrendingUp className="w-3 h-3" />}
                {analysis.load.direction === "down" && <TrendingDown className="w-3 h-3" />}
                {analysis.load.direction === "stable" && <Minus className="w-3 h-3" />}
                {analysis.load.vs_baseline_pct > 0 ? "+" : ""}{analysis.load.vs_baseline_pct}%
              </span>
            ) : null}
            badgeColor={
              analysis.load.direction === "up" ? "text-chart-1" : 
              analysis.load.direction === "down" ? "text-chart-4" : "text-chart-2"
            }
          />
        )}

        {/* Comparison Card */}
        {analysis?.comparison && (analysis.comparison.pace_delta || analysis.comparison.hr_delta) && (
          <SignalCard
            icon={GitCompare}
            title={t("analysis.comparison")}
            items={[
              analysis.comparison.pace_delta ? { label: t("analysis.paceDelta"), value: analysis.comparison.pace_delta } : null,
              analysis.comparison.hr_delta ? { label: t("analysis.hrDelta"), value: analysis.comparison.hr_delta } : null,
            ].filter(Boolean)}
          />
        )}
      </div>

      {/* Coach Insight */}
      {analysis?.insight && (
        <Card className="bg-card border-border mb-4">
          <CardContent className="p-4">
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
              {t("analysis.coachInsight")}
            </p>
            <p className="font-mono text-xs text-muted-foreground leading-relaxed" data-testid="coach-insight">
              {analysis.insight}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Guidance */}
      {analysis?.guidance && (
        <Card className="bg-primary/5 border-primary/20 mb-4">
          <CardContent className="p-4">
            <p className="font-mono text-xs text-primary leading-relaxed" data-testid="guidance">
              {analysis.guidance}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="space-y-2 mt-6">
        <Button
          onClick={goToDeepAnalysis}
          data-testid="deep-analysis-btn"
          className="w-full bg-primary text-white hover:bg-primary/90 rounded-none h-11 font-mono text-xs uppercase tracking-wider flex items-center justify-center gap-2"
        >
          <MessageSquare className="w-4 h-4" />
          {t("analysis.viewFullAnalysis")}
        </Button>
        <Button
          onClick={goToAskCoach}
          variant="ghost"
          data-testid="ask-coach-btn"
          className="w-full text-muted-foreground hover:text-foreground rounded-none h-10 font-mono text-xs uppercase tracking-wider"
        >
          {t("analysis.askCoach")}
        </Button>
      </div>
    </div>
  );
}

function SignalCard({ icon: Icon, title, items, badge, badgeColor }) {
  return (
    <Card className="bg-card border-border">
      <CardContent className="p-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2 mb-2">
            <Icon className="w-4 h-4 text-muted-foreground" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              {title}
            </span>
          </div>
          {badge && (
            <span className={`font-mono text-xs font-semibold ${badgeColor || ""}`}>
              {badge}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          {items.map((item, idx) => item && (
            <div key={idx}>
              <p className="font-mono text-sm font-semibold">{item.value || "--"}</p>
              <p className="font-mono text-[9px] text-muted-foreground uppercase">{item.label}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
