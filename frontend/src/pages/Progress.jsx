import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { Card, CardContent } from "@/components/ui/card";
import { useLanguage } from "@/context/LanguageContext";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  ResponsiveContainer,
  Tooltip,
  Cell
} from "recharts";
import { 
  TrendingUp, 
  Activity,
  ChevronRight,
  Bike,
  Footprints,
  Calendar
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const getWorkoutIcon = (type) => {
  switch (type) {
    case "cycle":
      return Bike;
    case "run":
    default:
      return Footprints;
  }
};

const formatDuration = (minutes) => {
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hrs > 0) {
    return `${hrs}h ${mins}m`;
  }
  return `${mins}m`;
};

const CustomTooltip = ({ active, payload, label, t }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-popover border border-border p-3">
        <p className="font-mono text-xs text-muted-foreground mb-1">{label}</p>
        <p className="font-mono text-sm font-medium">
          {payload[0].value.toFixed(1)} {t("dashboard.km")}
        </p>
      </div>
    );
  }
  return null;
};

export default function Progress() {
  const [stats, setStats] = useState(null);
  const [workouts, setWorkouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const { t, lang } = useLanguage();

  const dateLocale = t("dateFormat.locale");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, workoutsRes] = await Promise.all([
          axios.get(`${API}/stats`),
          axios.get(`${API}/workouts`)
        ]);
        setStats(statsRes.data);
        setWorkouts(workoutsRes.data);
      } catch (error) {
        console.error("Failed to fetch data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="p-6 md:p-8 animate-pulse">
        <div className="h-8 w-48 bg-muted rounded mb-8" />
        <div className="h-64 bg-muted rounded mb-8" />
      </div>
    );
  }

  // Prepare chart data with localized day names
  const chartData = stats?.weekly_summary?.map(day => ({
    date: new Date(day.date).toLocaleDateString(dateLocale, { weekday: "short" }),
    distance: day.distance,
    count: day.count
  })) || [];

  const typeData = stats?.workouts_by_type || {};

  return (
    <div className="p-6 md:p-8 pb-24 md:pb-8" data-testid="progress-page">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-heading text-2xl md:text-3xl uppercase tracking-tight font-bold mb-1">
          {t("progress.title")}
        </h1>
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          {t("progress.subtitle")}
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <Card className="metric-card bg-card border-border">
          <CardContent className="p-4 md:p-6">
            <div className="flex items-start justify-between mb-3">
              <span className="data-label">{t("progress.totalVolume")}</span>
              <TrendingUp className="w-4 h-4 text-chart-2" />
            </div>
            <p className="font-heading text-3xl md:text-4xl font-bold">
              {stats?.total_distance_km?.toFixed(0) || 0}
            </p>
            <p className="font-mono text-xs text-muted-foreground mt-1">{t("progress.kilometers")}</p>
          </CardContent>
        </Card>

        <Card className="metric-card bg-card border-border">
          <CardContent className="p-4 md:p-6">
            <div className="flex items-start justify-between mb-3">
              <span className="data-label">{t("progress.sessions")}</span>
              <Activity className="w-4 h-4 text-primary" />
            </div>
            <p className="font-heading text-3xl md:text-4xl font-bold">
              {stats?.total_workouts || 0}
            </p>
            <p className="font-mono text-xs text-muted-foreground mt-1">{t("progress.workouts")}</p>
          </CardContent>
        </Card>

        <Card className="metric-card bg-card border-border col-span-2 md:col-span-1">
          <CardContent className="p-4 md:p-6">
            <div className="flex items-start justify-between mb-3">
              <span className="data-label">{t("progress.byType")}</span>
              <Calendar className="w-4 h-4 text-muted-foreground" />
            </div>
            <div className="flex items-center gap-4">
              {Object.entries(typeData).map(([type, count]) => {
                const Icon = getWorkoutIcon(type);
                return (
                  <div key={type} className="flex items-center gap-2">
                    <Icon className="w-4 h-4 text-muted-foreground" />
                    <span className="font-mono text-sm">{count}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Distance Chart */}
      {chartData.length > 0 && (
        <div className="mb-8">
          <h2 className="font-heading text-lg uppercase tracking-tight font-semibold mb-4">
            {t("progress.dailyDistance")}
          </h2>
          <Card className="chart-container">
            <CardContent className="p-6">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis 
                    dataKey="date" 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10, fontFamily: "JetBrains Mono" }}
                  />
                  <YAxis 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10, fontFamily: "JetBrains Mono" }}
                  />
                  <Tooltip content={(props) => <CustomTooltip {...props} t={t} />} cursor={false} />
                  <Bar dataKey="distance" radius={[0, 0, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={entry.distance > 0 ? "hsl(var(--primary))" : "hsl(var(--muted))"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      )}

      {/* All Workouts */}
      <div>
        <h2 className="font-heading text-lg uppercase tracking-tight font-semibold mb-4">
          {t("progress.allWorkouts")}
        </h2>
        <div className="space-y-3">
          {workouts.map((workout, index) => {
            const Icon = getWorkoutIcon(workout.type);
            const typeLabel = t(`workoutTypes.${workout.type}`) || workout.type;
            return (
              <Link
                key={workout.id}
                to={`/workout/${workout.id}`}
                data-testid={`progress-workout-${workout.id}`}
                className="block animate-in"
                style={{ animationDelay: `${index * 30}ms` }}
              >
                <Card className="metric-card bg-card border-border hover:border-primary/30 transition-colors">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-4">
                      <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-muted border border-border">
                        <Icon className="w-5 h-5 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="workout-type-badge">
                            {typeLabel}
                          </span>
                          <span className="font-mono text-[10px] text-muted-foreground">
                            {new Date(workout.date).toLocaleDateString(dateLocale, {
                              month: "short",
                              day: "numeric"
                            })}
                          </span>
                        </div>
                        <p className="font-medium text-sm truncate">
                          {workout.name}
                        </p>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="font-mono text-sm font-medium">
                            {workout.distance_km.toFixed(1)} {t("dashboard.km")}
                          </p>
                          <p className="font-mono text-[10px] text-muted-foreground">
                            {formatDuration(workout.duration_minutes)}
                          </p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                      </div>
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
