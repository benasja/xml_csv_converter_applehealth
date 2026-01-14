# Apple Health XML to CSV Converter

Python utility that extracts key Apple Health metrics from an Apple Health export (`export.xml`) and writes them to a CSV (`full_health_data.csv`) for easier analysis.

## Quick start

1. Export Apple Health data
2. Unzip `export.zip` to get `export.xml` and place it in the same folder as `convert_health_data.py`.
3. Run the converter from a terminal:

`python convert_health_data.py`

After the script finishes you should find the CSV with the data. 

## Extracted metrics (TARGET_TYPES)

The converter focuses on these Apple Health identifiers:

```
HKQuantityTypeIdentifierStepCount
HKQuantityTypeIdentifierActiveEnergyBurned
HKQuantityTypeIdentifierHeartRate
HKQuantityTypeIdentifierRestingHeartRate
HKQuantityTypeIdentifierHeartRateVariabilitySDNN
HKCategoryTypeIdentifierSleepAnalysis
HKQuantityTypeIdentifierBodyMass
HKQuantityTypeIdentifierBodyFatPercentage
HKQuantityTypeIdentifierVO2Max
HKQuantityTypeIdentifierRespiratoryRate
HKCategoryTypeIdentifierAppleStandHour
```

## Using the CSV with an LLM (suggested prompt)

Paste the generated CSV into an LLM along with the following prompt and fill in the user context fields before submitting.

---

**UNIVERSAL HEALTH ANALYSIS PROMPT** (paste along with `full_health_data.csv`)

Role: You are an Elite Sports Physiologist and Health Data Scientist.
Task: Analyze the attached Apple Health data file (`full_health_data.csv`) to provide a comprehensive health audit, a "Biological Age" estimate, and actionable lifestyle recommendations.

**USER CONTEXT (fill before submitting)**

- Age: [INSERT AGE]
- Gender: [INSERT GENDER]
- Occupation/Lifestyle: [INSERT JOB (e.g., Student, Office Worker, Manual Labor)]
- Main Goal: [INSERT GOAL (e.g., Lose Fat, Build Muscle, Longevity, Marathon Prep)]

**ANALYSIS PROTOCOL — 5 Pillars**

1. THE ENGINE (Cardiovascular)
   - Data: Resting Heart Rate, VO2 Max
   - Ask: Compare to age-group norms; classify cardiovascular fitness.

2. THE MOVEMENT (Activity Baseline)
   - Data: Steps, Active Energy, Stand Hours
   - Ask: Identify sedentary patterns and consistency (weekday vs weekend).

3. THE METABOLISM (Body Composition)
   - Data: Body Mass, Body Fat %
   - Ask: Correlate weight trends with activity and energy expenditure.

4. THE RECOVERY (Nervous System)
   - Data: HRV (SDNN), Resting Heart Rate
   - Ask: Is HRV stable or dropping? Look for signs of stress or poor recovery.

5. THE IMMUNITY (Early Warning)
   - Data: Respiratory Rate
   - Ask: Look for spikes indicating illness, stress, or overtraining.

**OUTPUT FORMAT (requested)**

- Executive summary: Health Grade (A–F) and Biological Age estimate.
- The Good: Strong signals and wins.
- The Bad: Red flags and concerning trends.
- The Plan: Three concrete, data-backed habits to start immediately.

---
