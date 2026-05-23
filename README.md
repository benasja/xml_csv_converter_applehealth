# Apple Health XML to CSV Converter

Python utility that parses an Apple Health export (`export.xml`) and produces:

- **`full_health_data.csv`** — flat legacy export (all targeted record types + workouts + ECG metadata)
- **Coaching-ready aggregates** — daily, workout, and weekly summaries for analysis or LLM coaching

## Quick start

1. Export Apple Health data from the Health app.
2. Unzip `export.zip` and place `export.xml` (and optional `export_cda.xml`, `electrocardiograms/`) next to `convert_health_data.py`.
3. Run:

```bash
python3 convert_health_data.py
```

## Coaching outputs

| File | Description |
|------|-------------|
| `daily_metrics.csv` | One row per calendar day (local date from each record’s timezone offset) |
| `workout_summary.csv` | One row per workout with HR joined from samples in the workout window |
| `weekly_summary.csv` | One row per ISO week |
| `available_types.csv` | Every Health type seen in the export with counts |
| `data_quality_report.txt` | Date range, missingness, gaps, duplicate bursts |
| `coaching_types_usage.txt` | Which coaching types were present vs missing on the last run |

Units are normalized where possible: **kg**, **km**, **kcal**, **bpm**, **minutes**. Empty cells mean missing data (not zero).

### Daily columns (`daily_metrics.csv`)

`date`, `steps_total`, `active_kcal_total`, `basal_kcal_total`, `resting_hr_avg`, `hrv_sdnn_avg`, `sleep_in_bed_hours`, `sleep_asleep_hours`, `sleep_rem_hours`, `sleep_core_hours`, `sleep_deep_hours`, `body_mass_kg`, `body_fat_pct`, `vo2max`, `respiratory_rate_avg`, `stand_hours_met_count`

Sleep segments are attributed to the **wake day** (end date of the segment). Stage hours use Apple’s `HKCategoryValueSleepAnalysis*` values when present.

### Workout columns (`workout_summary.csv`)

Includes stable `workout_id`, activity label, timestamps (with offset), energy, distance, HR avg/max, optional **HR zones** (Z1–Z5 as % of max HR; default max **190 bpm** if not configured), and cycling power/cadence when present in `WorkoutStatistics` or time-aligned records.

### Weekly columns (`weekly_summary.csv`)

`iso_week`, session counts (strength / cycling / walking), `zone2_minutes_estimate` (sum of workout Z2 minutes), and weekly rollups of steps, sleep, resting HR, HRV, weight, body fat.

## Apple Health types used for coaching

**Daily / recovery metrics**

- `HKQuantityTypeIdentifierStepCount`
- `HKQuantityTypeIdentifierActiveEnergyBurned`
- `HKQuantityTypeIdentifierBasalEnergyBurned` (included when present in export)
- `HKQuantityTypeIdentifierRestingHeartRate`
- `HKQuantityTypeIdentifierHeartRateVariabilitySDNN`
- `HKCategoryTypeIdentifierSleepAnalysis` (InBed, Asleep, REM, Core, Deep)
- `HKQuantityTypeIdentifierBodyMass`
- `HKQuantityTypeIdentifierBodyFatPercentage`
- `HKQuantityTypeIdentifierVO2Max`
- `HKQuantityTypeIdentifierRespiratoryRate`
- `HKCategoryTypeIdentifierAppleStandHour`

**Workout enrichment (joined by time window)**

- `HKQuantityTypeIdentifierHeartRate` — avg/max and zone minutes per workout
- `HKQuantityTypeIdentifierCyclingPower`
- `HKQuantityTypeIdentifierCyclingCadence`
- Workout XML attributes: duration, total/active energy, distance, `WorkoutStatistics`, `sourceName`

**Legacy flat export (`full_health_data.csv`)** still uses the original 11 record types plus all workouts and ECG classification rows.

After each run, open **`data_quality_report.txt`** for the exact list of types **found vs missing** in your export.

## Sample data

A minimal fixture lives in `fixtures/sample_export.xml` for smoke testing:

```bash
cp fixtures/sample_export.xml export.xml
python3 convert_health_data.py
```

## Using the CSV with an LLM (suggested prompt)

Paste `daily_metrics.csv` and/or `workout_summary.csv` into an LLM with the prompt below (fill in user context).

---

**UNIVERSAL HEALTH ANALYSIS PROMPT**

Role: You are an Elite Sports Physiologist and Health Data Scientist.  
Task: Analyze the attached Apple Health coaching files to provide a health audit, a biological age estimate, and actionable recommendations.

**USER CONTEXT**

- Age: [INSERT AGE]
- Gender: [INSERT GENDER]
- Occupation/Lifestyle: [INSERT JOB]
- Main Goal: [INSERT GOAL]

**ANALYSIS PROTOCOL — 5 Pillars**

1. **Cardiovascular** — resting HR, VO2 max, workout HR zones  
2. **Movement** — steps, active energy, stand hours, weekly sessions  
3. **Metabolism** — weight, body fat trends  
4. **Recovery** — HRV, sleep stages, resting HR  
5. **Early warning** — respiratory rate spikes  

**OUTPUT FORMAT**

- Executive summary: Health grade (A–F) and biological age estimate  
- The Good / The Bad / The Plan (three concrete habits)

---
