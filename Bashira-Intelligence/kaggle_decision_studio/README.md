# Decision Studio Kaggle Pack

This folder replaces the old notebook workflow with a cleaner two-step process:

1. Export live SQL data locally into CSVs.
2. Upload those CSVs to Kaggle and run the training script there.

The Kaggle output is a fresh `wmr_results`-style package containing only the files the current Decision Studio UI needs:

- `ag_metrics.json`
- `risk_scores.csv`
- `feature_importance.csv`
- `priority_wells_final.csv`

## Local export

Run this from the repo root:

```powershell
cd "C:\Users\sagar\Downloads\Bashira-Intelligence (2)\Bashira-Intelligence"
.\ml_venv\Scripts\Activate.ps1
python kaggle_decision_studio\export_decision_studio_inputs.py
```

This creates:

```text
kaggle_decision_studio\inputs\
  wmr_full.csv
  wmr_latest.csv
  plan_snapshot.csv
  job_progress_report_gb.csv
  sap_drilling_sequence.csv
  manifest.json
```

## Kaggle run

Upload the whole `kaggle_decision_studio\inputs` folder as a Kaggle dataset.

Then in Kaggle:

```python
!python /kaggle/input/<your-dataset>/train_decision_studio_kaggle.py --input-dir /kaggle/input/<your-dataset> --output-dir /kaggle/working/wmr_results
```

If you upload the script separately, point to that script path instead.

## Download

After Kaggle finishes, download:

```text
/kaggle/working/wmr_results
```

That folder is the corrected package you can use instead of the stale Decision Studio outputs.

## What changed from the old notebook

- canonical well key is `pdo_well_id`
- `WMR_Full` is deduped by `pdo_well_id + snapshot_date`
- training uses time-based validation, not in-sample scoring
- outputs are aligned to the current Decision Studio metric surface
- no HTML report is generated, only the files the tab actually consumes
