# Wearable Dataset

This folder stores the mock wearable input dataset used by the demo morning check-in flow.

## Files

```text
unclean_smartwatch_health_data.csv
LICENSE
```

## License

The dataset is provided under the Apache License 2.0. Keep this `LICENSE` file with the dataset when distributing or modifying it.

If the original source provides a separate `NOTICE` file, add it to this folder as `NOTICE`.

## Expected Columns

The CSV is expected to include:

- `User ID`
- `Heart Rate (BPM)`
- `Blood Oxygen Level (%)`
- `Step Count`
- `Sleep Duration (hours)`
- `Activity Level`
- `Stress Level`

## App Mapping

The wearable loader will map dataset columns into the app's `WearableSnapshot` shape:

- `Heart Rate (BPM)` -> `resting_heart_rate`
- `Blood Oxygen Level (%)` -> `blood_oxygen_level`
- `Step Count` -> `step_count`
- `Sleep Duration (hours)` -> `sleep_hours`
- `Activity Level` -> `activity_level`
- `Stress Level` -> `stress_level`

The remaining check-in fields are derived or self-reported:

- `sleep_score`
- `energy_level`
- `soreness_quads`
- `soreness_upper`
- `pain_level`
- `available_minutes`

## Data Quality

The current file is intentionally unclean and includes missing values, outliers, inconsistent activity labels, and invalid values such as `ERROR`. The app should treat it as a simulation input source and clean each sampled row before passing it into the LangGraph workflow.
