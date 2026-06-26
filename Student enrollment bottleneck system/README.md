# Student Enrollment Bottleneck Detection System

A Flask web app that detects and forecasts enrollment system bottlenecks using Random Forest classification and LSTM time-series forecasting. Includes real-time system monitoring, live ML predictions, and a load simulation tool.

## Prerequisites

- **Python 3.11** (check with `python --version`)
- **uv** package manager (install from [astral.sh/uv](https://astral.sh/uv))

## Setup

```bash
# Clone the repo
git clone <repo-url>
cd enrollment_system_blessing

# Install all dependencies
uv sync

# Generate seed data (~65,000 system logs with bottleneck patterns)
uv run python scripts/seed_data.py
```

> **Note:** Pre-trained ML models are already included in `ml/models/`. Only run training below if you want to retrain from scratch (~30 minutes).

```bash
# Optional: retrain ML models from scratch
uv run python ml/train_models.py
```

## Running the App

```bash
uv run python main.py
```

Open **http://localhost:5000** in your browser.

## Login Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@university.edu` | `admin123` |
| Student | `student0001@university.edu` | `password123` |

You can also register a new student account from the login page.

## Using the App

### As a Student

1. **Register** or log in with the credentials above
2. **Enroll** — click "Enroll in Course", pick a course, and complete payment (use any Luhn-valid card number, e.g. `4111 1111 1111 1111`)
3. **Traffic Light** — the dashboard shows a green/yellow/red indicator telling you whether now is a good time to enroll
4. **My Enrollments / My Payments** — view your enrollment history and payment records

### As an Admin

1. **Dashboard** — live system stats, Chart.js real-time forecast with bottleneck predictions, recent logs and enrollments
2. **Predictions page** — Random Forest classification, LSTM forecast, 24-hour bottleneck prediction table
3. **Manage** — view/add students, browse courses, review all enrollments and payments, inspect system logs
4. **The chart** — shows actual requests (solid blue), forecasted requests (dashed), red triangles for predicted bottleneck minutes, orange for moderate, with a red "NOW" line separating actual from forecast

## Load Testing

The app includes a load simulation script. **Start the server first**, then run the test in a separate terminal.

```bash
# Basic: 50 users, 10 concurrent, mixed scenario
uv run python scripts/load_test.py

# Heavy: 200 users, 20 concurrent, bottleneck scenario
uv run python scripts/load_test.py --users 200 --concurrent 20 --scenario bottleneck
```

### Scenarios

| Scenario | What it does |
|----------|-------------|
| `register` | Simulates student registration only |
| `enroll` | Logs in existing students and enrolls them in courses |
| `pay` | Logs in and processes payments |
| `mixed` | Random mix of register, login, enroll, and pay |
| `bottleneck` | All actions simultaneously with high concurrency — designed to overwhelm the server |

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--users` | 50 | Number of virtual users to simulate |
| `--concurrent` | 10 | Max concurrent workers |
| `--scenario` | mixed | One of: register, enroll, pay, mixed, bottleneck |
| `--base-url` | http://127.0.0.1:5000 | Server URL to test against |
| `--no-cleanup` | off | Keep test users in database after run |

### What to Watch

1. Run a heavy load test: `uv run python scripts/load_test.py --users 300 --concurrent 50 --scenario bottleneck`
2. While it runs (or immediately after), open the **admin dashboard** in the browser
3. The **real-time forecast chart** will show red bottleneck zones extending into the future
4. The **system status banner** will turn red with a critical alert
5. Refresh the **student dashboard** — the traffic light will change from green to red

## How It Works

- **Every request** logs real CPU usage, memory, active users, and response time to the database
- **Random Forest** classifies each log entry as Normal, Moderate, or Bottleneck
- **LSTM** forecasts request count and response time 60 minutes ahead
- **Combined decision engine** merges both models to generate alerts, traffic light advice, and forecast predictions
- **Background retraining** retrains both models every 5 minutes if at least 100 new log entries have accumulated — runs as a daemon thread, never blocks the server

## Tech Stack

Python 3.11, Flask, SQLAlchemy, SQLite, scikit-learn (Random Forest), TensorFlow/Keras (LSTM), psutil, Chart.js
