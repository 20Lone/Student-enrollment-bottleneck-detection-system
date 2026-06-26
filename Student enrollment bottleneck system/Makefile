.PHONY: install run seed train-rf train-lstm train load clean package help

PYTHON := .venv/bin/python
PIP := .venv/bin/pip
FLASK_RUN := $(PYTHON) main.py

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

run: ## Run the Flask dev server
	$(FLASK_RUN)

seed: ## Seed the database with minute-level data
	$(PYTHON) scripts/seed_data.py

train-rf: ## Train Random Forest classifier
	$(PYTHON) -c "from ml.random_forest import train_random_forest; train_random_forest()"

train-lstm: ## Train LSTM forecaster (~30 min)
	$(PYTHON) -c "from ml.lstm_model import train_lstm; train_lstm(sequence_length=60)"

train: train-rf train-lstm ## Train both RF and LSTM models

load: ## Run load test (usage: make load USERS=50 SCENARIO=bottleneck)
	$(PYTHON) scripts/load_test.py --users $(USERS) --scenario $(SCENARIO)

load-mixed: ## Run mixed load test with 100 users
	$(PYTHON) scripts/load_test.py --users 100 --scenario mixed

clean: ## Remove Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -type f -name "*.pyc" -delete 2>/dev/null; \
	true

package: clean ## Create project zip excluding .git, .venv, __pycache__, models, db
	@echo "Creating enrollment_system_blessing.zip..."
	@zip -r enrollment_system_blessing.zip . \
		-x ".git/*" \
		-x ".venv/*" \
		-x "venv/*" \
		-x "env/*" \
		-x "__pycache__/*" \
		-x "*__pycache__*" \
		-x "*.pyc" \
		-x "instance/*" \
		-x "ml/models/*" \
		-x "*.log" \
		-x "*/.DS_Store" \
		-x ".DS_Store" \
		-x "Thumbs.db" \
		-x "*.egg-info/*" \
		-x ".vscode/*" \
		-x ".idea/*" \
		-x "ml/evaluation_report.txt" \
		-x "enrollment_system_blessing.zip"
	@echo "Done: enrollment_system_blessing.zip"
	@ls -lh enrollment_system_blessing.zip
