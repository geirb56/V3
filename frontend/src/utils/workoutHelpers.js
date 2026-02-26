import { Bike, Footprints } from "lucide-react";

export const getWorkoutIcon = (type) => {
  const iconMap = {
    cycle: Bike,
    run: Footprints,
  };
  return iconMap[type] || Footprints;
};

export const formatDuration = (minutes) => {
  if (!minutes) return "--";
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hrs > 0) return `${hrs}h ${mins}m`;
  return `${mins}m`;
};

export const formatDate = (dateStr, locale, options = {}) => {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const defaultOptions = { month: "short", day: "numeric", ...options };
  return date.toLocaleDateString(locale, defaultOptions);
};

export const getLoadColor = (signal) => {
  const colors = {
    high: "text-chart-1",
    low: "text-chart-4",
  };
  return colors[signal] || "text-chart-2";
};

export const getTrendIcon = (trend) => {
  const { TrendingUp, TrendingDown, Minus } = require("lucide-react");
  const map = {
    up: TrendingUp,
    down: TrendingDown,
  };
  return map[trend] || Minus;
};

export const getTrendColor = (trend) => {
  const colors = {
    up: "text-chart-2",
    down: "text-chart-4",
  };
  return colors[trend] || "text-muted-foreground";
};
