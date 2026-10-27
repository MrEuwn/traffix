"""Dataset and ML inference path tests."""

import numpy as np

from ml.forecast.features import FEATURE_COLUMNS
from ml.predictor import prediction_service
from ml.registry import registry
from sim.dataset_loader import HybridTrafficDatasetLoader


class IdentityScaler:
    """Feature/target scaler test double."""

    def transform(self, matrix):
        assert matrix.shape[1] == len(FEATURE_COLUMNS)
        return matrix

    def inverse_transform(self, value):
        return value


class FakeModel:
    """Keras model test double that records the window it received."""

    def __init__(self):
        self.last_input = None

    def __call__(self, model_input, training=False):
        self.last_input = np.asarray(model_input)
        return np.asarray([[123.0]])


def test_dataset_loader_normalizes_data_team_csv():
    loader = HybridTrafficDatasetLoader()
    metadata = loader.get_dataset_metadata()
    assert metadata.rows > 0
    assert metadata.intersections == 6

    rows = loader.get_rows()
    assert rows[0].intersection_id == "INT-001"
    assert {row.intersection_id for row in rows[:8]} == {
        "INT-001",
        "INT-002",
        "INT-003",
        "INT-004",
        "INT-005",
        "INT-006",
    }


def _install_fakes(seq_len: int) -> dict[str, FakeModel]:
    models = {"15m": FakeModel(), "2h": FakeModel(), "4h": FakeModel()}
    registry.clear()
    registry.set_artifacts(
        models=models,
        scalers={"feat": IdentityScaler(), "target": {h: IdentityScaler() for h in models}},
        config={"seq_len": {h: seq_len for h in models}},
    )
    registry.set_fallback_mode(False)
    return models


def test_lstm_receives_real_history_window_not_repeated_rows():
    rows = HybridTrafficDatasetLoader().get_rows()
    # Replay minute 120 for INT-001: enough history for a 60-minute window.
    batch = [r for r in rows if r.intersection_id == "INT-001"][120:121]
    models = _install_fakes(seq_len=60)
    prediction_service.note_dataset_batch(batch)

    result = prediction_service.predict("INT-001", "15m")
    assert result.source == "lstm"
    assert result.predicted_vehicle_count == 123
    window = models["15m"].last_input
    assert window.shape == (1, 60, len(FEATURE_COLUMNS))
    # A real window varies over time; the old code repeated one row 60 times.
    assert not np.allclose(window[0, 0], window[0, -1])
    # The window ends at the replayed minute itself, never after it.
    assert result.issue_time_wib is not None and result.target_time_wib is not None
    registry.clear()


def test_without_history_the_heuristic_is_labelled_and_never_reads_targets():
    rows = HybridTrafficDatasetLoader().get_rows()
    batch = [r for r in rows if r.intersection_id == "INT-001"][5:6]  # 5 minutes of history only
    _install_fakes(seq_len=60)
    prediction_service.note_dataset_batch(batch)

    result = prediction_service.predict("INT-001", "2h")
    assert result.source == "heuristic"
    assert result.expected_mae is None
    assert result.predicted_vehicle_count != int(round(batch[0].target_volume_2h or -1))
    registry.clear()
