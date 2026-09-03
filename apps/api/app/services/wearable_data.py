import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock

from app.schemas import MorningSelfReport, WearableSnapshot

DATASET_PATH = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "raw"
    / "wearables"
    / "unclean_smartwatch_health_data.csv"
)
_sample_lock = Lock()
_sample_index = 0


class WearableDatasetUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class CleanWearableRow:
    heart_rate_bpm: int
    blood_oxygen_level: float
    step_count: int
    sleep_duration_hours: float
    activity_level: str
    stress_level: int


class WearableDataService:
    """Mock smartwatch adapter for the demo morning check-in flow."""

    def __init__(self, dataset_path: Path = DATASET_PATH) -> None:
        self.dataset_path = dataset_path

    # This method samples a wearable snapshot from the dataset, using the provided self-report to fill in soreness and pain levels. 
    def sample_snapshot(self, self_report: MorningSelfReport) -> WearableSnapshot:
        rows = _load_clean_rows(str(self.dataset_path))
        if not rows:
            raise WearableDatasetUnavailable(f"No valid wearable rows found in {self.dataset_path}")

        row = _next_row(rows)
        return WearableSnapshot(
            sleep_hours=row.sleep_duration_hours,
            sleep_score=_derive_sleep_score(row.sleep_duration_hours),
            resting_heart_rate=row.heart_rate_bpm,
            blood_oxygen_level=row.blood_oxygen_level,
            step_count=row.step_count,
            activity_level=row.activity_level,
            stress_level=row.stress_level,
            soreness_quads=self_report.soreness_quads,
            soreness_upper=self_report.soreness_upper,
            energy_level=_derive_energy_level(row),
            pain_level=self_report.pain_level,
            available_minutes=self_report.available_minutes,
        )


@lru_cache(maxsize=1) # cache the results of loading the dataset so we don't have to read the CSV file every time we sample a snapshot
def _load_clean_rows(dataset_path: str) -> list[CleanWearableRow]:
    path = Path(dataset_path) # check if the dataset file exists, and raise an error if it doesn't
    if not path.exists():
        raise WearableDatasetUnavailable(f"Wearable dataset not found: {path}")

    clean_rows: list[CleanWearableRow] = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for raw in csv.DictReader(file):
            row = _clean_row(raw)
            if row is not None:
                clean_rows.append(row)

    return clean_rows # returns a list of clean and valid rows from the CSV file


def _next_row(rows: list[CleanWearableRow]) -> CleanWearableRow:
    global _sample_index
    with _sample_lock:
        row = rows[_sample_index % len(rows)]
        _sample_index += 1
        return row

# this function takes a raw row from the CSV and returns a CleanWearableRow if the data is valid, or None if it's invalid
def _clean_row(row: dict[str, str]) -> CleanWearableRow | None: 
    heart_rate = _number(row.get("Heart Rate (BPM)"))
    blood_oxygen = _number(row.get("Blood Oxygen Level (%)"))
    step_count = _number(row.get("Step Count"))
    sleep_hours = _number(row.get("Sleep Duration (hours)"))
    stress_level = _number(row.get("Stress Level"))
    activity_level = _normalize_activity_level(row.get("Activity Level", ""))

    if heart_rate is None or not 35 <= heart_rate <= 130:
        return None
    if blood_oxygen is None or not 85 <= blood_oxygen <= 100:
        return None
    if step_count is None or not 0 <= step_count <= 50000:
        return None
    if sleep_hours is None or not 0 <= sleep_hours <= 14:
        return None
    if stress_level is None or not 0 <= stress_level <= 10:
        return None
    if activity_level == "unknown":
        return None

    return CleanWearableRow( # if row survives the above constrains, return a CleanWearableRow with the cleaned values
        heart_rate_bpm=round(heart_rate),
        blood_oxygen_level=round(blood_oxygen, 1),
        step_count=round(step_count),
        sleep_duration_hours=round(sleep_hours, 1),
        activity_level=activity_level,
        stress_level=round(stress_level),
    )


def _number(value: str | None) -> float | None: # turns a string into a float (or None if it can't be parsed)
    try:
        text = str(value or "").strip() # remove whitespace and convert None to empty string
        return float(text) if text else None
    except ValueError:
        return None


def _normalize_activity_level(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_") # eg. "Moderately Active" -> "moderately_active"
    if normalized in {"sedentary", "low", "low_active"}:
        return "low_active"
    if normalized in {"active", "actve", "moderate", "moderately_active"}:
        return "moderately_active"
    if normalized in {"highly_active", "very_active"}:
        return "highly_active"
    return "unknown"


def _derive_sleep_score(sleep_hours: float) -> int:
    if sleep_hours >= 8:
        return 92
    if sleep_hours >= 7:
        return 82
    if sleep_hours >= 6:
        return 68
    if sleep_hours >= 5:
        return 48
    return 32


def _derive_energy_level(row: CleanWearableRow) -> int:
    score = 5
    score += 2 if row.sleep_duration_hours >= 7 else -2
    score -= 2 if row.stress_level >= 7 else 0
    score += 1 if row.activity_level == "highly_active" and row.step_count < 16000 else 0
    return _clamp_int(score, 1, 10)


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
