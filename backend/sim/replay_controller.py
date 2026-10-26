"""Dataset replay cursor controller for Traffix simulation ticks."""

from sim.dataset_loader import HybridTrafficDatasetLoader
from sim.dataset_models import DatasetRow


class ReplayController:
    """Sequential replay cursor over hybrid traffic dataset rows."""

    def __init__(
        self,
        dataset_loader: HybridTrafficDatasetLoader | None = None,
        start_tick: int | None = None,
    ) -> None:
        """Initialize the replay controller.

        Args:
            dataset_loader: Optional dataset loader dependency.
            start_tick: Optional replay start position in dataset minutes. When
                omitted, `settings.replay_start_tick` is used (default 06:00) so
                a demo opens on the morning peak instead of midnight.
        """
        self._dataset_loader = dataset_loader or HybridTrafficDatasetLoader()
        self._rows: list[DatasetRow] | None = None
        self._cursor = 0
        self._start_tick = start_tick
        self._start_applied = False

    @property
    def start_tick(self) -> int:
        """Resolved replay start position in dataset minutes."""
        if self._start_tick is None:
            from core.config import settings

            self._start_tick = int(settings.replay_start_tick)
        return int(self._start_tick)

    def _load_rows(self) -> list[DatasetRow]:
        """Load and cache replay rows.

        Returns:
            Cached dataset rows in replay order.
        """
        if self._rows is None:
            self._rows = self._dataset_loader.get_rows()
        return self._rows

    def reset(self) -> None:
        """Reset the replay cursor to the configured start position."""
        rows = self._load_rows()
        self._cursor = self._start_index(rows)

    def _start_index(self, rows: list[DatasetRow]) -> int:
        """Return the row index of the configured start tick.

        Args:
            rows: Replay rows in timestamp order.

        Returns:
            Zero-based index of the first row at or after `start_tick` minutes
            from the beginning of the dataset (0 when the offset is not found).
        """
        start_tick = self.start_tick
        if start_tick <= 0 or not rows:
            return 0
        first_timestamp = rows[0].timestamp
        for index, row in enumerate(rows):
            elapsed_minutes = int(
                (row.timestamp - first_timestamp).total_seconds() // 60,
            )
            if elapsed_minutes >= start_tick:
                return index
        return 0

    def _apply_start_offset(self) -> None:
        """Jump to the configured start tick once, before the first batch."""
        if self._start_applied:
            return
        self._start_applied = True
        rows = self._load_rows()
        if rows:
            self._cursor = self._start_index(rows)

    def get_cursor(self) -> int:
        """Return current replay cursor position.

        Returns:
            Current zero-based cursor index.
        """
        return self._cursor

    def has_rows(self) -> bool:
        """Return whether the replay dataset has rows.

        Returns:
            True when at least one row is available.
        """
        return len(self._load_rows()) > 0

    def next_batch(self) -> list[DatasetRow]:
        """Return the next timestamp batch and advance the replay cursor.

        Returns:
            Rows sharing the next replay timestamp. Returns an empty list when
            the dataset has no rows.
        """
        rows = self._load_rows()
        if not rows:
            return []

        self._apply_start_offset()

        if self._cursor >= len(rows):
            self._cursor = 0

        current_timestamp = rows[self._cursor].timestamp
        batch: list[DatasetRow] = []

        while self._cursor < len(rows):
            row = rows[self._cursor]
            if row.timestamp != current_timestamp:
                break
            batch.append(row)
            self._cursor += 1

        return batch
