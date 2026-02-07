import { useState, useEffect } from "react";
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
  Calendar,
  Scale
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

export default function Dashboard() {
  const [insight, setInsight] = useState(null);
  const [workouts, setWorkouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const { t, lang } = useLanguage();

  useEffect(() => {
    fetchData();
  }, [lang]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [insightRes, workoutsRes] = await Promise.all([
        axios.get(`${API}/dashboard/insight?language=${lang}`),
        axios.get(`${API}/workouts`)
      ]);
      setInsight(insightRes.data);
      setWorkouts(workoutsRes.data);
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

  const getLoadBg = (signal) => {
    if (signal === "high") return "bg-chart-1/10";
    if (signal === "low") return "bg-chart-4/10";
    return "bg-chart-2/10";
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

  return (
    <div className="p-4 pb-24" data-testid="dashboard">
      {/* 1) COACH INSIGHT - TOP PRIORITY */}
      {insight?.coach_insight && (
        <Card className="bg-primary/5 border-primary/20 mb-4">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <Lightbulb className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
              <p className="font-mono text-sm text-primary leading-relaxed" data-testid="coach-insight">
                {insight.coach_insight}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 2) CURRENT WEEK - VOLUME FOCUS */}
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

      {/* 3) LAST MONTH - CONTEXT ONLY */}
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
