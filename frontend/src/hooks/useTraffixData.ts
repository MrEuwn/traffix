import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../lib/api";
import type {
  BottleneckPerIntersection,
  BottleneckResponse,
  Intersection,
  CctvFramesResponse,
  DetectionEvidence,
  ForecastEvaluationResponse,
  ForecastSeries,
  LiveInferenceResult,
  ModelEvaluationResponse,
  Prediction,
  Recommendation,
  SegmentsResponse,
  SegmentsSummaryResponse,
  SignalsSummaryResponse,
  SimulationResult,
  Weather,
  SystemStatus,
} from "../types";

const POLL = 1000;
/** Poling analitik v4 (dataset replay) — lebih lambat dari live metrics. */
const ANALYTICS_POLL = 5000;

export const useSystemStatus = () =>
  useQuery({
    queryKey: ["system-status"],
    queryFn: () => api.get("/api/v1/system/status").then(unwrap<SystemStatus>),
    refetchInterval: POLL,
  });

export const useIntersections = () =>
  useQuery({
    queryKey: ["intersections"],
    queryFn: () =>
      api
        .get("/api/v1/intersections")
        .then(unwrap<{ count: number; intersections: Intersection[] }>),
    refetchInterval: POLL,
    select: (d) => d.intersections,
  });

export const usePredictions = (intersectionId: string) =>
  useQuery({
    queryKey: ["predictions", intersectionId],
    queryFn: () =>
      api
        .get(`/api/v1/predictions/${intersectionId}`)
        .then(
          unwrap<{
            predictions: Prediction[];
            ml_mode: string;
            ml_fallback_active: boolean;
            ml_models_loaded: boolean;
          }>,
        ),
    refetchInterval: POLL,
    enabled: !!intersectionId,
  });

export const useRecommendations = () =>
  useQuery({
    queryKey: ["recommendations"],
    queryFn: () =>
      api
        .get("/api/v1/recommendations")
        .then(unwrap<{ count: number; recommendations: Recommendation[] }>),
    refetchInterval: POLL,
    select: (d) => d.recommendations,
  });

export const useSimulation = (
  intersectionId: string | null,
  enabled: boolean,
) =>
  useQuery({
    queryKey: ["simulation", intersectionId],
    queryFn: () =>
      api
        .get(`/api/v1/recommendations/${intersectionId}/simulate`)
        .then(unwrap<SimulationResult>)
        .catch(() => null),
    refetchInterval: 2000,
    enabled: enabled && !!intersectionId,
    retry: false,
  });

export const useWeather = () =>
  useQuery({
    queryKey: ["weather"],
    queryFn: () => api.get("/api/v1/weather/current").then(unwrap<Weather>),
    refetchInterval: 30000,
  });

export const useWeatherByIntersection = (intersectionId: string) =>
  useQuery({
    queryKey: ["weather", intersectionId],
    queryFn: () =>
      api
        .get(`/api/v1/weather/current?intersection_id=${intersectionId}`)
        .then(unwrap<Weather>),
    refetchInterval: 30000,
    enabled: !!intersectionId,
  });

export const useSimulationControls = () => {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["system-status"] });
    qc.invalidateQueries({ queryKey: ["intersections"] });
  };

  const start = useMutation({
    mutationFn: () => api.post("/api/v1/simulation/start"),
    onSuccess: invalidate,
  });

  const stop = useMutation({
    mutationFn: () => api.post("/api/v1/simulation/stop"),
    onSuccess: invalidate,
  });

  return { start, stop };
};

export const useManualOverride = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      intersectionId,
      greenDurationSeconds,
      durationMinutes = 5,
    }: {
      intersectionId: string;
      greenDurationSeconds: number;
      durationMinutes?: number;
    }) =>
      api.post(`/api/v1/intersections/${intersectionId}/manual-override`, {
        green_duration_seconds: greenDurationSeconds,
        duration_minutes: durationMinutes,
      }).catch((err) => { throw err; }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["intersections"] });
    },
  });
};

export const useClearManualOverride = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (intersectionId: string) =>
      api.delete(`/api/v1/intersections/${intersectionId}/manual-override`)
        .catch((err) => { throw err; }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["intersections"] });
    },
  });
};

/* ─────────────── Analitik v4 (SCHEMA-v4 §3.3) ─────────────── */

export const useBottlenecks = () =>
  useQuery({
    queryKey: ["bottlenecks"],
    queryFn: () => api.get("/api/v1/bottlenecks").then(unwrap<BottleneckResponse>),
    refetchInterval: ANALYTICS_POLL,
  });

export const useBottlenecksByIntersection = (intersectionId: string) =>
  useQuery({
    queryKey: ["bottlenecks", intersectionId],
    queryFn: () =>
      api
        .get(`/api/v1/bottlenecks/${intersectionId}`)
        .then(unwrap<BottleneckPerIntersection>),
    refetchInterval: ANALYTICS_POLL,
    enabled: !!intersectionId,
  });

export const useSegments = () =>
  useQuery({
    queryKey: ["segments"],
    queryFn: () => api.get("/api/v1/segments").then(unwrap<SegmentsResponse>),
    refetchInterval: ANALYTICS_POLL,
  });

export const useSegmentsSummary = () =>
  useQuery({
    queryKey: ["segments-summary"],
    queryFn: () => api.get("/api/v1/segments/summary").then(unwrap<SegmentsSummaryResponse>),
    refetchInterval: ANALYTICS_POLL,
  });

export const useSignalsSummary = (scope: "all" | "perempatan" | "pertigaan" = "all") =>
  useQuery({
    queryKey: ["signals-summary", scope],
    queryFn: () =>
      api
        .get(`/api/v1/signals/summary?scope=${scope}`)
        .then(unwrap<SignalsSummaryResponse>),
    refetchInterval: ANALYTICS_POLL,
  });

export const useModelEvaluation = () =>
  useQuery({
    queryKey: ["model-evaluation"],
    queryFn: () => api.get("/api/v1/model/evaluation").then(unwrap<ModelEvaluationResponse>),
    refetchInterval: ANALYTICS_POLL,
  });

/** Evaluasi D2 tugas utama: LSTM vs baseline per horizon + status runtime. */
export const useForecastEvaluation = () =>
  useQuery({
    queryKey: ["forecast-evaluation"],
    queryFn: () =>
      api.get("/api/v1/model/evaluation/forecast").then(unwrap<ForecastEvaluationResponse>),
    refetchInterval: ANALYTICS_POLL,
  });

export const useForecastSeries = (horizon: string, intersection: string | null) =>
  useQuery({
    queryKey: ["forecast-series", horizon, intersection],
    queryFn: () =>
      api
        .get(`/api/v1/model/evaluation/forecast/${horizon}/series`, {
          params: { step: 5, ...(intersection ? { intersection } : {}) },
        })
        .then(unwrap<ForecastSeries>),
    staleTime: Infinity,
  });

export const useDetectionEvidence = () =>
  useQuery({
    queryKey: ["detection-evidence"],
    queryFn: () => api.get("/api/v1/model/evaluation/detection").then(unwrap<DetectionEvidence>),
    staleTime: 60_000,
  });

export const useCctvFrames = () =>
  useQuery({
    queryKey: ["cctv-frames"],
    queryFn: () => api.get("/api/v1/cameras/frames").then(unwrap<CctvFramesResponse>),
    staleTime: 60_000,
  });

/** Jalankan YOLO sekarang pada satu frame rekaman (inferensi nyata di backend). */
export const useLiveInference = () =>
  useMutation({
    mutationFn: (frameId: string) =>
      api
        .post(`/api/v1/cameras/frames/${encodeURIComponent(frameId)}/infer`, null, { timeout: 60_000 })
        .then(unwrap<LiveInferenceResult>),
  });

// Notifikasi dari perubahan intersection state
export interface Notification {
  id: string;
  type: "warning" | "critical" | "info" | "success";
  message: string;
  intersection_id?: string;
  timestamp: string;
  read: boolean;
}

export const useNotifications = () => {
  const { data: intersections = [] } = useIntersections();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const prevRef = useRef<Record<string, number>>({});

  useEffect(() => {
    if (!intersections.length) return;
    const newNotifs: Notification[] = [];

    intersections.forEach((ix) => {
      const prev = prevRef.current[ix.intersection_id];
      const curr = ix.occupancy_rate;

      if (prev !== undefined) {
        if (curr >= 0.75 && prev < 0.75) {
          newNotifs.push({
            id: `${ix.intersection_id}-${Date.now()}`,
            type: "critical",
            message: `Kemacetan kritis terdeteksi di ${ix.intersection_name}`,
            intersection_id: ix.intersection_id,
            timestamp: new Date().toISOString(),
            read: false,
          });
        } else if (curr >= 0.45 && prev < 0.45) {
          newNotifs.push({
            id: `${ix.intersection_id}-${Date.now()}`,
            type: "warning",
            message: `Kemacetan sedang terdeteksi di ${ix.intersection_name}`,
            intersection_id: ix.intersection_id,
            timestamp: new Date().toISOString(),
            read: false,
          });
        } else if (curr < 0.45 && prev >= 0.45) {
          newNotifs.push({
            id: `${ix.intersection_id}-${Date.now()}`,
            type: "success",
            message: `Lalu lintas kembali normal di ${ix.intersection_name}`,
            intersection_id: ix.intersection_id,
            timestamp: new Date().toISOString(),
            read: false,
          });
        }
      }
      prevRef.current[ix.intersection_id] = curr;
    });

    if (newNotifs.length) {
      setNotifications((prev) => [...newNotifs, ...prev].slice(0, 20));
    }
  }, [intersections]);

  const markAllRead = () =>
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));

  const unreadCount = notifications.filter((n) => !n.read).length;

  return { notifications, markAllRead, unreadCount };
};
