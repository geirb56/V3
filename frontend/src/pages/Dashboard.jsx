import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Activity, 
  Timer, 
  Heart, 
  TrendingUp,
  ChevronRight,
  Bike,
  Footprints
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

const formatPace = (paceMinKm) => {
  if (!paceMinKm) return "--";
  const mins = Math.floor(paceMinKm);
  const secs = Math.round((paceMinKm - mins) * 60);
  return `${mins}:${secs.toString().padStart(2, "0")}/km`;
};

export default function Dashboard() {
  const [workouts, setWorkouts] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [workoutsRes, statsRes] = await Promise.all([
          axios.get(`${API}/workouts`),
          axios.get(`${API}/stats`)
        ]);
        setWorkouts(workoutsRes.data);
        setStats(statsRes.data);
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
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-muted rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 pb-24 md:pb-8" data-testid="dashboard">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-heading text-2xl md:text-3xl uppercase tracking-tight font-bold mb-1">
          Training Log
        </h1>
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          {new Date().toLocaleDateString("en-US", { 
            weekday: "long", 
            month: "short", 
            day: "numeric" 
          })}
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 stagger-children">
        <Card className="metric-card bg-card border-border animate-in">
          <CardContent className="p-4 md:p-6">
            <div className="flex items-start justify-between mb-3">
              <span className="data-label">Total Workouts</span>
              <Activity className="w-4 h-4 text-primary" />
            </div>
            <p className="font-heading text-3xl md:text-4xl font-bold">
              {stats?.total_workouts || 0}
            </p>
          </CardContent>
        </Card>

        <Card className="metric-card bg-card border-border animate-in">
          <CardContent className="p-4 md:p-6">
            <div className="flex items-start justify-between mb-3">
              <span className="data-label">Distance</span>
              <TrendingUp className="w-4 h-4 text-chart-2" />
            </div>
            <p className="font-heading text-3xl md:text-4xl font-bold">
              {stats?.total_distance_km?.toFixed(0) || 0}
            </p>
            <p className="font-mono text-xs text-muted-foreground mt-1">km</p>
          </CardContent>
        </Card>

        <Card className="metric-card bg-card border-border animate-in">
          <CardContent className="p-4 md:p-6">
            <div className="flex items-start justify-between mb-3">
              <span className="data-label">Duration</span>
              <Timer className="w-4 h-4 text-chart-3" />
            </div>
            <p className="font-heading text-3xl md:text-4xl font-bold">
              {Math.round((stats?.total_duration_minutes || 0) / 60)}
            </p>
            <p className="font-mono text-xs text-muted-foreground mt-1">hours</p>
          </CardContent>
        </Card>

        <Card className="metric-card bg-card border-border animate-in">
          <CardContent className="p-4 md:p-6">
            <div className="flex items-start justify-between mb-3">
              <span className="data-label">Avg HR</span>
              <Heart className="w-4 h-4 text-chart-4" />
            </div>
            <p className="font-heading text-3xl md:text-4xl font-bold">
              {stats?.avg_heart_rate?.toFixed(0) || "--"}
            </p>
            <p className="font-mono text-xs text-muted-foreground mt-1">bpm</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Workouts */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-heading text-lg uppercase tracking-tight font-semibold">
            Recent Workouts
          </h2>
          <Link 
            to="/progress" 
            data-testid="view-all-workouts"
            className="font-mono text-xs uppercase tracking-wider text-primary hover:text-primary/80 flex items-center gap-1"
          >
            View All <ChevronRight className="w-3 h-3" />
          </Link>
        </div>

        <ScrollArea className="h-[400px] md:h-auto">
          <div className="space-y-3">
            {workouts.slice(0, 5).map((workout, index) => {
              const Icon = getWorkoutIcon(workout.type);
              return (
                <Link
                  key={workout.id}
                  to={`/workout/${workout.id}`}
                  data-testid={`workout-card-${workout.id}`}
                  className="block animate-in"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <Card className="metric-card bg-card border-border hover:border-primary/30 transition-colors">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-4">
                        {/* Icon */}
                        <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-muted border border-border">
                          <Icon className="w-5 h-5 text-muted-foreground" />
                        </div>

                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="workout-type-badge">
                              {workout.type}
                            </span>
                            <span className="font-mono text-[10px] text-muted-foreground">
                              {new Date(workout.date).toLocaleDateString("en-US", {
                                month: "short",
                                day: "numeric"
                              })}
                            </span>
                          </div>
                          <p className="font-medium text-sm truncate">
                            {workout.name}
                          </p>
                        </div>

                        {/* Stats */}
                        <div className="flex items-center gap-6 text-right">
                          <div>
                            <p className="font-mono text-sm font-medium">
                              {workout.distance_km.toFixed(1)} km
                            </p>
                            <p className="font-mono text-[10px] text-muted-foreground">
                              {formatDuration(workout.duration_minutes)}
                            </p>
                          </div>
                          <div className="hidden md:block">
                            <p className="font-mono text-sm font-medium">
                              {workout.avg_heart_rate || "--"} bpm
                            </p>
                            <p className="font-mono text-[10px] text-muted-foreground">
                              {workout.type === "run" 
                                ? formatPace(workout.avg_pace_min_km)
                                : `${workout.avg_speed_kmh?.toFixed(1) || "--"} km/h`
                              }
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
        </ScrollArea>
      </div>
    </div>
  );
}
