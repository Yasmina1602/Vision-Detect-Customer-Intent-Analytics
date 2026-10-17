# Vision Detect — Basic edition
API_DIR = apps/api
DASH_DIR = apps/dashboard
ifeq ($(OS),Windows_NT)
  PY = $(API_DIR)/.venv/Scripts/python
else
  PY = $(API_DIR)/.venv/bin/python
endif

.PHONY: install migrate api dashboard build test

install:
	python -m venv $(API_DIR)/.venv
	$(PY) -m pip install -r $(API_DIR)/requirements.txt
	cd $(DASH_DIR) && npm install

migrate:
	cd $(API_DIR) && ../../$(PY) -m alembic upgrade head

api:
	cd $(API_DIR) && ../../$(PY) -m uvicorn app.main:app --reload --port 8000

dashboard:
	cd $(DASH_DIR) && npm run dev

build:
	cd $(DASH_DIR) && npm run build

test:
	cd $(API_DIR) && ../../$(PY) -m pytest -q
