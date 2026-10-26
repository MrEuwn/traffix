export interface Intersection {
  intersection_id: string;
  intersection_name: string;
  vehicle_count: number;
  avg_speed: number;
  occupancy_rate: number;
  queue_length: number;
  signal_state: "GREEN" | "YELLOW" | "RED";
  green_duration_seconds: number;
  weather_condition: string;
  ai_predictions: Record<string, number>;
  ai_insight?: string;
  ai_recommendation?: string;
  congestion_level?: string;
  yolo_source?: Record<string, any>;
  last_updated: string;
}

export interface Prediction {
  intersection_id: string;
  horizon: string;
  predicted_vehicle_count: number;
  predicted_congestion_level: string;
  confidence_score: number;
  prediction_timestamp: string;
  source: "lstm" | "dataset" | "heuristic";
}

export interface Recommendation {
  intersection_id: string;
  current_green_seconds: number;
  recommended_green_seconds: number;
  delta_seconds: number;
  reason: string;
  congestion_risk_percent: number;
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
}

export interface Weather {
  scope?: string;
  condition: string;
  temperature_celsius?: number;
  humidity_percent?: number;
  distribution?: Record<string, number>;
  intersections?: number;
  observed_at?: string;
}

export interface SystemStatus {
  service: string;
  status: string;
  ml_ready: boolean;
  ml_models_loaded: boolean;
  ml_fallback_active: boolean;
  ml_mode: string;
  weather_ready: boolean;
  simulation_ready: boolean;
  simulation_active: boolean;
  dataset_ready: boolean;
  camera_ready: boolean;
  supported_horizons: string[];
}

export interface SimulationMetrics {
  vehicle_count: number;
  avg_speed: number;
  queue_length: number;
  occupancy_rate: number;
  congestion_level: string;
}

export interface SimulationResult {
  intersection_id: string;
  current_green_seconds: number;
  proposed_green_seconds: number;
  delta_seconds: number;
  current: SimulationMetrics;
  projected: SimulationMetrics;
  improvements: {
    queue_reduction_pct: number;
    speed_gain_pct: number;
    throughput_gain_pct: number;
    occupancy_reduction_pct: number;
  };
  risk_before: number;
  risk_after: number;
  summary: string;
}

/* ─────────────── v4 analytics (SCHEMA-v4 §5) ─────────────── */

export interface BottleneckCause {
  cause: string;
  sections: number;
  share: number;
  avg_vc_ratio: number;
  avg_queue_veh: number;
  avg_wait_time_min: number;
}

export interface BottleneckPerIntersection {
  intersection_id: string;
  intersection_name: string;
  tipe_persimpangan: "perempatan" | "pertigaan";
  dominant_cause: string;
  confidence: number;
  probabilities: Record<string, number>;
  top3: { cause: string; probability: number }[];
  drivers: string[];
  model_available?: boolean;
  /** hanya pada GET /bottlenecks/{id} */
  history?: {
    tick: number;
    timestamp_wib: string;
    dominant_cause: string;
    confidence: number;
    vc_ratio: number;
    queue_length_veh: number;
    avg_speed_kmh: number;
  }[];
  /** hanya pada GET /bottlenecks/{id} */
  sections?: SegmentItem[];
}

export interface BottleneckResponse {
  tick: number;
  timestamp_wib: string;
  section_count: number;
  affected_section_count: number;
  dominant_cause: string;
  causes: BottleneckCause[];
  per_intersection: BottleneckPerIntersection[];
}

export interface SegmentVehicleMix {
  roda_2: number;
  roda_3: number;
  roda_4: number;
  roda_6plus: number;
  total: number;
  smp_ekivalen: number;
  persen: {
    roda_2: number;
    roda_3: number;
    roda_4: number;
    roda_6plus: number;
  };
}

export interface SegmentItem {
  section_id: string;
  nama_ruas: string;
  section_type: "approach" | "corridor" | string;
  intersection_id: string;
  /** kosong untuk section_type corridor */
  tipe_persimpangan: string;
  /** kosong untuk section_type corridor */
  approach: string;
  panjang_m: number;
  jumlah_lajur: number;
  kapasitas_smp_per_jam: number;
  kapasitas_kendaraan: number;
  volume_veh_per_hour: number;
  vc_ratio: number;
  los: string;
  avg_speed_kmh: number;
  queue_length_veh: number;
  wait_time_min: number;
  kendaraan: SegmentVehicleMix;
  bottleneck_cause: string;
  penyebab_dominan: string;
}

export interface SegmentsResponse {
  tick: number;
  count: number;
  total_capacity_vehicles: number;
  items: SegmentItem[];
}

export interface SegmentsSummaryResponse {
  tick: number;
  section_count: number;
  approach_count: number;
  corridor_count: number;
  total_capacity_vehicles: number;
  total_capacity_smp_per_jam: number;
  total_kendaraan: SegmentVehicleMix;
  avg_vc_ratio: number;
  avg_speed_kmh: number;
  los_distribution: Record<string, number>;
  per_intersection: { intersection_id: string; section_count: number }[];
}

export interface SignalPerIntersection {
  intersection_id: string;
  intersection_name: string;
  tipe_persimpangan: "perempatan" | "pertigaan";
  jumlah_lengan: number;
  cycle_length_s: number;
  avg_green_s: number;
  avg_red_s: number;
  avg_wait_time_min: number;
  avg_queue_veh: number;
  avg_delay_s: number;
}

export interface SignalsSummaryResponse {
  scope: string;
  timestamp_wib: string;
  intersection_count: number;
  section_count: number;
  cycle_length_s: number;
  avg_green_s: number;
  avg_red_s: number;
  avg_wait_time_min: number;
  avg_queue_veh: number;
  avg_delay_s: number;
  /** agregat per scope (perempatan / pertigaan) */
  items: {
    scope: string;
    intersection_count: number;
    section_count: number;
    cycle_length_s: number;
    avg_green_s: number;
    avg_red_s: number;
    avg_wait_time_min: number;
    avg_queue_veh: number;
    avg_delay_s: number;
  }[];
  per_intersection: SignalPerIntersection[];
}

export interface ModelBaselineScore {
  model: string;
  macro_f1: number;
  balanced_accuracy: number;
  accuracy: number;
}

export interface ModelPerClassScore {
  cause: string;
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

/** Semua field turunan artefak opsional: backend mengirim `available: false` bila model belum ada. */
export interface ModelEvaluationResponse {
  available: boolean;
  model_name: string;
  trained_at?: string;
  classes?: string[];
  split?: { train: string; validation: string; test: string; protocol: string };
  metrics?: { macro_f1: number; balanced_accuracy: number; accuracy: number };
  baselines?: {
    majority_class: ModelBaselineScore;
    rule_based: ModelBaselineScore;
  };
  per_class?: ModelPerClassScore[];
  confusion_matrix?: { labels: string[]; matrix: number[][] };
  feature_importance?: { feature: string; importance: number }[];
  leakage_guard?: string[];
  limitations?: string[];
  artifacts?: { model: string; metrics: string };
}
