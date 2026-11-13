# IPL Data Analysis Dashboard (FastAPI + Streamlit)

## 1. Project structure

```text
ipl_dashboard_project/
│
├── data/
│   ├── matches.csv
│   └── deliveries.csv
│
├── backend.py
├── app.py
└── requirements.txt
```

## 2. Dataset

Download an IPL ball-by-ball dataset containing `matches.csv` and `deliveries.csv`.
Place both files inside the `data` folder.

The code expects common columns:
- matches.csv: `id`, `season`, `team1`, `team2`, `winner`
- deliveries.csv: `match_id`, `batting_team`, `bowling_team`, `batsman`,
  `bowler`, `batsman_runs`, `total_runs`, `wide_runs`, `noball_runs`,
  `bye_runs`, `legbye_runs`, `player_dismissed`, `dismissal_kind`

## 3. Install dependencies

Open a terminal in this project folder:

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
.env\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
venv\Scripts\activate
```

Install packages:

```bash
pip install -r requirements.txt
```

## 4. Start the backend

Open terminal 1:

```bash
uvicorn backend:app --reload
```

Open API documentation:

http://127.0.0.1:8000/docs

Check backend and dataset:

http://127.0.0.1:8000/health

## 5. Start the frontend

Open terminal 2 in the same project folder and activate the virtual environment:

```bash
streamlit run app.py
```

Streamlit normally opens:

http://localhost:8501

## 6. Useful API endpoints

- `GET /health`
- `GET /seasons`
- `GET /teams`
- `GET /summary?season=All`
- `GET /team-performance?season=All`
- `GET /top-batsmen?season=All&limit=10`
- `GET /top-bowlers?season=All&limit=10`
- `GET /team-comparison?team1=...&team2=...&season=All`

## Notes

- Start FastAPI before Streamlit.
- Keep both terminals running.
- If you change the CSV files, restart FastAPI.
- Player and team statistics are calculated from the selected dataset. This is a historical analysis project, not a live-score application.
- Bowling economy and batting strike rate use standard ball-by-ball calculations; dataset conventions and unusual deliveries can affect reported figures.
