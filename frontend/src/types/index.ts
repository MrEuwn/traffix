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
  /** Volume simpang yang diramalkan, kend/jam (nama field lama dipertahankan). */
  predicted_vehicle_count: number;
  predicted_congestion_level: string;
  /** Tidak ada skor keyakinan terkalibrasi — selalu null. */
  confidence_score: number | null;
  prediction_timestamp: string;
  source: "lstm" | "heuristic";
  unit: string;
  current_volume: number | null;
  issue_time_wib: string | null;
  target_time_wib: string | null;
  /** MAE LSTM pada replay v4 hari 7 (dari artefak evaluasi); null untuk heuristik. */
  expected_mae: number | null;
  /** Peran hari replay ini di evaluasi D2: latih (in-sample), validasi, atau uji. */
  replay_split: "latih" | "validasi" | "uji" | null;
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
  forecaster?: ForecasterStatus;
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
  label_provenance?: string;
  reproduction?: {
    matches_stored_metrics: boolean;
    generated_at?: string;
    validation: { macro_f1: number; balanced_accuracy: number; accuracy: number; n: number };
    command: string;
  };
}

/* ── D2: peramalan volume (tugas utama) ── */

export interface ForecasterStatus {
  mode: "lstm" | "heuristic_fallback" | "disabled";
  label: string;
  model_files: Record<string, string>;
  loaded_sha256: Record<string, string | null>;
  evaluated_sha256: Record<string, string>;
  matches_evaluation: boolean;
  evaluation_generated_at: string | null;
  input_data: { kind: string; path: string; features_ready: boolean; features_error: string | null };
}

export interface RegressionMetrics {
  n: number;
  mae: number;
  rmse: number;
  wape_pct: number;
  smape_pct: number;
  mape_pct: number;
  mape_zero_targets_skipped: number;
  r2: number;
  bias: number;
}

export interface ForecastComparisonRow {
  model: string;
  label: string;
  role: "model" | "baseline" | "pembanding";
  test: RegressionMetrics;
  validation: { mae: number; rmse: number; wape_pct: number };
  lstm_mae_improvement_pct: number | null;
  lstm_wape_improvement_pct: number | null;
  lstm_mae_abs_diff: number | null;
}

export interface ForecastHorizonResult {
  horizon_minutes: number;
  n: { train: number; validation: number; test: number };
  comparison: ForecastComparisonRow[];
  strongest_baseline: { model: string; chosen_by: string };
  lstm_vs_strongest_baseline: {
    mae_improvement_pct: number;
    wape_improvement_pct: number;
    bootstrap: { mae_diff: number; ci95_low: number; ci95_high: number; block_minutes: number; reps: number };
    significant: boolean;
  };
  best_on_test: { model: string; mae: number };
  selection: Record<string, Record<string, unknown>>;
  error_by_target_hour: { hour: number; n: number; lstm_mae: number; baseline_mae: number }[];
  worst_cases: {
    intersection_id: string;
    issue_time_wib: string;
    target_time_wib: string;
    actual: number;
    lstm: number;
    abs_error: number;
  }[];
  predictions_csv: string;
}

export interface ForecastEvaluationResponse {
  available: boolean;
  reason?: string;
  command?: string;
  task?: string;
  question?: string;
  target?: { definition: string; unit: string; horizons: Record<string, number> };
  model?: {
    name: string;
    version: string;
    selected_config: Record<string, Record<string, unknown>>;
    artifacts: Record<string, { file: string; sha256: string }>;
  };
  dataset?: {
    name: string;
    provenance: string;
    provenance_detail: string;
    sha256: string;
    rows: number;
    intersections: number;
    why_this_dataset: string;
  };
  secondary_experiment?: {
    key: string;
    title: string;
    dataset: string;
    horizons: Record<string, ForecastHorizonResult>;
  };
  split?: { protocol: string; train: string; validation: string; test: string; test_period: string[] };
  metric_definitions?: Record<string, string>;
  horizons?: Record<string, ForecastHorizonResult>;
  transfer_v4?: {
    dataset: string;
    split: string;
    horizons: Record<string, { lstm: RegressionMetrics; persistence: RegressionMetrics; mae_improvement_pct_vs_persistence: number }>;
  };
  legacy_reproduction?: {
    protocol: string;
    n_test: number;
    test_period: string[];
    horizons: Record<string, { recomputed: RegressionMetrics; stored_mape_pct: number; mape_matches_stored: boolean; persistence_last_observation: RegressionMetrics }>;
    issues_found: string[];
  };
  leakage_guard?: string[];
  limitations?: string[];
  not_claims?: string[];
  figures?: string[];
  reproduce?: string;
  generated_at?: string;
  git_commit?: string | null;
  git_dirty?: boolean | null;
  seed?: number;
  runtime: ForecasterStatus;
}

export interface ForecastSeries {
  horizon: string;
  baseline: string;
  unit: string;
  step_minutes: number;
  intersection: string | null;
  intersections: string[];
  n_total: number;
  source_csv: string;
  points: { t: string; actual: number; lstm: number; baseline: number }[];
}

/* ── YOLO: frame CCTV rekaman + bukti validasi ── */

export interface DetectionBox {
  xyxy: [number, number, number, number];
  confidence: number;
  class: string;
}

export interface CctvFrame {
  frame_id: string;
  period: "pagi" | "siang" | "malam";
  video: string;
  second: string;
  width: number;
  height: number;
  vehicle_count: number;
  by_class?: Record<string, number>;
  /** Jumlah kotak dari model tim (best.pt) pada frame yang sama — pembanding. */
  team_model_vehicle_count?: number;
  mean_confidence: number | null;
  inference_ms: number;
  boxes: DetectionBox[];
  ruas?: string | null;
  location?: string | null;
  recorded_at_wib?: string | null;
  temperature_c?: number | null;
  precipitation_mm?: number | null;
}

export interface CctvFramesResponse {
  available: boolean;
  reason?: string;
  mode?: "precomputed";
  source?: { kind: string; description: string };
  model?: {
    weights: string;
    sha256: string;
    description?: string;
    classes: string[];
    ultralytics_version: string;
    conf_threshold: number;
    imgsz: number;
    mode?: "full" | "sliced";
  };
  team_model?: { weights: string; classes: string[]; imgsz: number };
  caveats?: string[];
  summary?: {
    frames: number;
    by_period: Record<string, { frames: number; mean_vehicle_count: number; mean_team_model_count?: number }>;
    mean_vehicle_count?: number;
    mean_team_model_count?: number;
    by_class_total?: Record<string, number>;
    mean_inference_ms: number;
  };
  generated_at?: string;
  frames?: CctvFrame[];
  live_inference_available: boolean;
  live_inference_reason: string | null;
}

export interface LiveInferenceResult {
  frame_id: string;
  mode: "live";
  conf_threshold: number;
  vehicle_count: number;
  inference_ms: number;
  boxes: DetectionBox[];
  width: number;
  height: number;
}

export interface DetectionEvidence {
  available?: boolean;
  generated_at?: string;
  recorded_validation?: {
    split: string;
    source: string;
    reproduced_in_this_run: boolean;
    why_not_reproduced: string;
    dataset: string;
    images: Record<string, number>;
    val_instances: number | null;
    ultralytics: { precision: number | null; recall: number | null; map50: number | null; map50_95: number | null };
    iou50_matching_conf025: Record<string, number | null>;
    caveats: string[];
  };
  frame_inference?: {
    path: string;
    summary: CctvFramesResponse["summary"];
    model: NonNullable<CctvFramesResponse["model"]>;
    team_model?: CctvFramesResponse["team_model"];
    generated_at: string;
  } | null;
  live_inference_available: boolean;
  live_inference_reason: string | null;
}
