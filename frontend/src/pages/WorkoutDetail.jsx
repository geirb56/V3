import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  ArrowLeft, 
  Timer, 
  Heart, 
  TrendingUp, 
  Mountain,
  Flame,
  Bike,
  Footprints,
  Activity
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

const zoneColors = {
  z1: "bg-chart-2",  // Green - Recovery
  z2: "bg-chart-1",  // Blue - Aerobic
  z3: "bg-chart-3",  // Yellow - Tempo
  z4: "bg-chart-3",  // Orange - Threshold
  z5: "bg-chart-4",  // Red - VO2Max
};

const zoneLabels = {
  z1: "Z1 Recovery",
  z2: "Z2 Aerobic",
  z3: "Z3 Tempo",
  z4: "Z4 Threshold",
  z5: "Z5 VO2Max",
};

export default function WorkoutDetail() {
  const { id } = useParams();
  const [workout, setWorkout] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchWorkout = async () => {
      try {
        const res = await axios.get(`${API}/workouts/${id}`);
        setWorkout(res.data);
      } catch (error) {
        console.error("Failed to fetch workout:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchWorkout();
  }, [id]);

  if (loading) {
    return (
      <div className="p-6 md:p-8 animate-pulse">
        <div className="h-8 w-32 bg-muted rounded mb-8" />
        <div className="h-12 w-64 bg-muted rounded mb-4" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-muted rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (!workout) {
    return (
      <div className="p-6 md:p-8" data-testid="workout-not-found">
        <Link to="/" className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground mb-8">
          <ArrowLeft className="w-4 h-4" />
          <span className="font-mono text-xs uppercase tracking-wider">Back</span>
        </Link>
        <p className="text-muted-foreground">Workout not found.</p>
      </div>
    );
  }

  const Icon = getWorkoutIcon(workout.type);
  const zones = workout.effort_zone_distribution || {};

  return (
    <div className="p-6 md:p-8 pb-24 md:pb-8" data-testid="workout-detail">
      {/* Back Link */}
      <Link 
        to="/" 
        data-testid="back-to-dashboard"
        className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground mb-8 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span className="font-mono text-xs uppercase tracking-wider">Back</span>
      </Link>

      {/* Header */}
      <div className="flex items-start gap-4 mb-8">
        <div className="w-12 h-12 flex items-center justify-center bg-muted border border-border">
          <Icon className="w-6 h-6 text-muted-foreground" />
        </div>
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="workout-type-badge">{workout.type}</span>
            <span className="font-mono text-xs text-muted-foreground">
              {new Date(workout.date).toLocaleDateString("en-US", {
                weekday: "long",
                month: "long",
                day: "numeric",
                year: "numeric"
              })}
            </span>
          </div>
          <h1 className="font-heading text-2xl md:text-3xl uppercase tracking-tight font-bold">
            {workout.name}
          </h1>
        </div>
      </div>

      {/* Primary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 stagger-children">
        <MetricCard
          label="Distance"
          value={workout.distance_km.toFixed(1)}
          unit="km"
          icon={TrendingUp}
          color="text-chart-2"
        />
        <MetricCard
          label="Duration"
          value={formatDuration(workout.duration_minutes)}
          icon={Timer}
          color="text-chart-3"
        />
        <MetricCard
          label="Avg Heart Rate"
          value={workout.avg_heart_rate || "--"}
          unit="bpm"
          icon={Heart}
          color="text-chart-4"
        />
        <MetricCard
          label={workout.type === "run" ? "Avg Pace" : "Avg Speed"}
          value={workout.type === "run" 
            ? formatPace(workout.avg_pace_min_km)
            : `${workout.avg_speed_kmh?.toFixed(1) || "--"}`
          }
          unit={workout.type === "run" ? "" : "km/h"}
          icon={Activity}
          color="text-primary"
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <MetricCard
          label="Max Heart Rate"
          value={workout.max_heart_rate || "--"}
          unit="bpm"
          icon={Heart}
          color="text-chart-4"
          small
        />
        <MetricCard
          label="Elevation"
          value={workout.elevation_gain_m || "--"}
          unit="m"
          icon={Mountain}
          color="text-muted-foreground"
          small
        />
        <MetricCard
          label="Calories"
          value={workout.calories || "--"}
          unit="kcal"
          icon={Flame}
          color="text-chart-3"
          small
        />
        <div /> {/* Empty cell for grid alignment */}
      </div>

      {/* Zone Distribution */}
      {Object.keys(zones).length > 0 && (
        <div className="mb-8">
          <h2 className="font-heading text-lg uppercase tracking-tight font-semibold mb-4">
            Effort Distribution
          </h2>
          <Card className="bg-card border-border">
            <CardContent className="p-6">
              <div className="space-y-4">
                {Object.entries(zones).map(([zone, percentage]) => (
                  <div key={zone} data-testid={`zone-${zone}`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                        {zoneLabels[zone] || zone}
                      </span>
                      <span className="font-mono text-sm font-medium">
                        {percentage}%
                      </span>
                    </div>
                    <div className="zone-bar">
                      <div 
                        className={`zone-bar-fill ${zoneColors[zone] || "bg-muted-foreground"}`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Notes */}
      {workout.notes && (
        <div className="mb-8">
          <h2 className="font-heading text-lg uppercase tracking-tight font-semibold mb-4">
            Notes
          </h2>
          <Card className="bg-card border-border">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground">{workout.notes}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Analyze Button */}
      <Link to="/coach" data-testid="analyze-with-coach">
        <Button className="bg-primary text-white hover:bg-primary/90 rounded-none uppercase font-bold tracking-wider text-xs h-11 px-8">
          Analyze with Coach
        </Button>
      </Link>
    </div>
  );
}

function MetricCard({ label, value, unit, icon: Icon, color, small }) {
  return (
    <Card className="metric-card bg-card border-border animate-in">
      <CardContent className={small ? "p-4" : "p-4 md:p-6"}>
        <div className="flex items-start justify-between mb-2">
          <span className="data-label">{label}</span>
          {Icon && <Icon className={`w-4 h-4 ${color}`} />}
        </div>
        <p className={`font-heading font-bold ${small ? "text-xl md:text-2xl" : "text-2xl md:text-3xl"}`}>
          {value}
        </p>
        {unit && (
          <p className="font-mono text-xs text-muted-foreground mt-1">{unit}</p>
        )}
      </CardContent>
    </Card>
  );
}
