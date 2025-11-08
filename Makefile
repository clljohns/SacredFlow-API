SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.SILENT:
.DEFAULT_GOAL := menu

# -------------------------------------------------------------------
# Shared paths
# -------------------------------------------------------------------
RUN_DIR := .make
PID_DIR := $(RUN_DIR)/pids
LOG_DIR := $(RUN_DIR)/logs

$(PID_DIR) $(LOG_DIR):
	mkdir -p $@

# -------------------------------------------------------------------
# Funnel (Vite app) configuration
# -------------------------------------------------------------------
FUNNEL_DIR ?= $(HOME)/MaluLani_Subscription_Funnel
FUNNEL_HOST ?= 127.0.0.1
FUNNEL_PORT ?= 5173
FUNNEL_PID := $(PID_DIR)/funnel.pid
FUNNEL_LOG := $(LOG_DIR)/funnel.log
FUNNEL_PID_ABS := $(abspath $(FUNNEL_PID))
FUNNEL_LOG_ABS := $(abspath $(FUNNEL_LOG))

# -------------------------------------------------------------------
# API (FastAPI) configuration
# -------------------------------------------------------------------
API_DIR ?= $(CURDIR)
API_VENV ?= venv
API_APP ?= app.main:app
API_HOST ?= 0.0.0.0
API_PORT ?= 8000
API_PID := $(PID_DIR)/api.pid
API_LOG := $(LOG_DIR)/api.log
API_PID_ABS := $(abspath $(API_PID))
API_LOG_ABS := $(abspath $(API_LOG))
PYTHON_BIN := $(API_VENV)/bin/python
PIP_BIN := $(API_VENV)/bin/pip
UVICORN_BIN := $(API_VENV)/bin/uvicorn
ALEMBIC_BIN := $(API_VENV)/bin/alembic

.PHONY: menu help target-list
menu:
	@if [ -t 0 ]; then \
		bash ./scripts/control.sh; \
	else \
		echo "Interactive menu requires a TTY. Showing target list instead."; \
		$(MAKE) --no-print-directory target-list; \
	fi

help: target-list

target-list:
	@echo "SacredFlow Make targets:"
	@echo "  setup-all        Install dependencies for both funnel and API"
	@echo "  funnel-install   Install funnel NPM deps"
	@echo "  funnel-start     Start funnel dev server (background)"
	@echo "  funnel-start-custom Start funnel dev server on a custom port"
	@echo "  funnel-stop      Stop funnel dev server"
	@echo "  funnel-restart   Restart funnel dev server"
	@echo "  funnel-build     Build funnel production bundle"
	@echo "  funnel-lint      Run funnel lint checks"
	@echo "  funnel-status    Show funnel process status"
	@echo "  funnel-logs      Tail funnel logs"
	@echo "  funnel-push      Commit+push funnel repo with prompted message"
	@echo "  funnel-kill-port Force kill any process using the funnel port"
	@echo "  api-setup        Alias for api-install (kept for symmetry)"
	@echo "  api-install      Create venv and install API deps"
	@echo "  api-start        Start FastAPI dev server (background)"
	@echo "  api-start-custom Start FastAPI dev server on a custom port"
	@echo "  api-stop         Stop FastAPI server"
	@echo "  api-restart      Restart FastAPI server"
	@echo "  api-lint         Byte-compile API sources"
	@echo "  api-status       Show API process status"
	@echo "  api-logs         Tail API logs"
	@echo "  api-migrate      Run Alembic migrations"
	@echo "  api-push         Commit+push API repo with prompted message"
	@echo "  api-kill-port    Force kill any process using the API port"
	@echo "  start-all        Start funnel + API together"
	@echo "  stop-all         Stop funnel + API"
	@echo "  restart-all      Restart funnel + API"
	@echo "  status-all       Show combined status summary"
	@echo "  diagnostics      Print port usage and recent logs"
	@echo ""
	@echo "Tip: run 'make' for the interactive control center."

.PHONY: ensure-funnel-dir ensure-api-dir
ensure-funnel-dir:
	@if [ ! -d "$(FUNNEL_DIR)" ]; then \
		echo "Funnel directory $(FUNNEL_DIR) not found. Override FUNNEL_DIR=<path>."; \
		exit 1; \
	fi

ensure-api-dir:
	@if [ ! -d "$(API_DIR)" ]; then \
		echo "API directory $(API_DIR) not found. Override API_DIR=<path>."; \
		exit 1; \
	fi

$(PYTHON_BIN):
	python3 -m venv $(API_VENV)
	$(PYTHON_BIN) -m pip install --upgrade pip

.PHONY: check-npm check-python check-git check-node check-lsof
check-npm:
	@command -v npm >/dev/null 2>&1 || { echo "Error: npm is not installed or not on PATH."; exit 1; }

check-node:
	@command -v node >/dev/null 2>&1 || { echo "Error: node is not installed or not on PATH."; exit 1; }

check-python:
	@command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is not installed."; exit 1; }

check-git:
	@command -v git >/dev/null 2>&1 || { echo "Error: git is not installed."; exit 1; }

check-lsof:
	@command -v lsof >/dev/null 2>&1 || command -v ss >/dev/null 2>&1 || { echo "Warning: neither lsof nor ss is available; some diagnostics may be limited."; }

.PHONY: setup-all start-all stop-all restart-all status-all diagnostics api-setup
setup-all: check-npm check-node check-python
	@echo "==> Installing funnel dependencies"
	@$(MAKE) --no-print-directory funnel-install
	@echo "==> Installing API dependencies"
	@$(MAKE) --no-print-directory api-install

start-all:
	@echo "==> Starting funnel"
	@$(MAKE) --no-print-directory funnel-start
	@echo "==> Starting API"
	@$(MAKE) --no-print-directory api-start

stop-all:
	@echo "==> Stopping API"
	@$(MAKE) --no-print-directory api-stop
	@echo "==> Stopping funnel"
	@$(MAKE) --no-print-directory funnel-stop

restart-all:
	@echo "==> Restarting services"
	@$(MAKE) --no-print-directory stop-all || true
	@$(MAKE) --no-print-directory start-all

status-all:
	@echo "==> Funnel status"
	@$(MAKE) --no-print-directory funnel-status || true
	@echo ""
	@echo "==> API status"
	@$(MAKE) --no-print-directory api-status || true

diagnostics: check-lsof
	@echo "===================================================="
	@echo " SacredFlow Diagnostics"
	@echo "===================================================="
	@$(MAKE) --no-print-directory status-all || true
	@echo ""
	@echo "-- Port usage ($(FUNNEL_PORT), $(API_PORT)) --"
	@if command -v lsof >/dev/null 2>&1; then \
		for port in $(FUNNEL_PORT) $(API_PORT); do \
			echo "Port $$port:"; \
			lsof -nPi :$$port || echo "  no listeners"; \
			echo ""; \
		done; \
	elif command -v ss >/dev/null 2>&1; then \
		echo "lsof not available; showing ss output"; \
		ss -ltnp | grep -E '(:$(FUNNEL_PORT)|:$(API_PORT))' || echo "No listeners reported by ss."; \
	else \
		echo "Neither lsof nor ss commands are available to inspect ports."; \
	fi
	@echo ""
	@echo "-- Recent Funnel log --"
	@if [ -f "$(FUNNEL_LOG)" ]; then \
		tail -n 20 "$(FUNNEL_LOG)"; \
	else \
		echo "No funnel logs yet."; \
	fi
	@echo ""
	@echo "-- Recent API log --"
	@if [ -f "$(API_LOG)" ]; then \
		tail -n 20 "$(API_LOG)"; \
	else \
		echo "No API logs yet."; \
	fi

api-setup: api-install

.PHONY: funnel-install
funnel-install: check-npm check-node ensure-funnel-dir
	cd "$(FUNNEL_DIR)"
	npm install

.PHONY: funnel-start
funnel-start: check-npm check-node ensure-funnel-dir $(PID_DIR) $(LOG_DIR)
	if [ -f "$(FUNNEL_PID)" ] && ps -p $$(cat "$(FUNNEL_PID)") >/dev/null 2>&1; then
		echo "Funnel already running (PID $$(cat "$(FUNNEL_PID)"))."
	else
		if command -v lsof >/dev/null 2>&1; then \
			port_pids=$$(lsof -ti:$(FUNNEL_PORT) 2>/dev/null | tr '\n' ' '); \
			if [ -n "$$port_pids" ]; then \
				echo "Port $(FUNNEL_PORT) is already in use by: $$port_pids"; \
				echo "Stop the listed process or run with FUNNEL_PORT=<port> make funnel-start."; \
				exit 1; \
			fi; \
		fi
		cd "$(FUNNEL_DIR)"
		if [ ! -d "node_modules" ]; then
			echo "node_modules missing. Running npm install first..."
			npm install
		fi
		echo "Starting funnel dev server on $(FUNNEL_HOST):$(FUNNEL_PORT)..."
		nohup npm run dev -- --host $(FUNNEL_HOST) --port $(FUNNEL_PORT) >> "$(FUNNEL_LOG_ABS)" 2>&1 &
		new_pid=$$!
		sleep 1
		if ps -p $$new_pid >/dev/null 2>&1; then
			echo $$new_pid > "$(FUNNEL_PID_ABS)"
			echo "Funnel dev server started (PID $$new_pid). Logs: $(FUNNEL_LOG_ABS)"
		else
			echo "Funnel failed to start. See recent logs below:"
			tail -n 40 "$(FUNNEL_LOG_ABS)" || true
			rm -f "$(FUNNEL_PID)"
			exit 1
		fi
	fi

.PHONY: funnel-start-custom
funnel-start-custom:
	@read -rp "Enter funnel port (default $(FUNNEL_PORT)): " custom_port; \
	custom_port=$${custom_port:-$(FUNNEL_PORT)}; \
	if ! [[ $$custom_port =~ ^[0-9]+$$ ]]; then \
		echo "Port must be numeric."; \
		exit 1; \
	fi; \
	$(MAKE) --no-print-directory FUNNEL_PORT=$$custom_port funnel-start

.PHONY: funnel-stop
funnel-stop:
	if [ -f "$(FUNNEL_PID)" ]; then
		pid=$$(cat "$(FUNNEL_PID)")
		if ps -p $$pid >/dev/null 2>&1; then
			kill $$pid
			echo "Stopped funnel process $$pid."
		else
			echo "Funnel PID $$pid is stale."
		fi
		rm -f "$(FUNNEL_PID)"
	else
		echo "Funnel server is not running."
	fi

.PHONY: funnel-restart
funnel-restart:
	$(MAKE) funnel-stop
	$(MAKE) funnel-start

.PHONY: funnel-build
funnel-build: check-npm check-node ensure-funnel-dir
	cd "$(FUNNEL_DIR)"
	npm run build

.PHONY: funnel-lint
funnel-lint: check-npm check-node ensure-funnel-dir
	cd "$(FUNNEL_DIR)"
	npm run lint

.PHONY: funnel-status
funnel-status:
	if [ -f "$(FUNNEL_PID)" ]; then
		pid=$$(cat "$(FUNNEL_PID)")
		if ps -p $$pid >/dev/null 2>&1; then
			echo "Funnel running (PID $$pid) on $(FUNNEL_HOST):$(FUNNEL_PORT)."
		else
			echo "Funnel PID file exists but process $$pid is not running."
			rm -f "$(FUNNEL_PID)"
		fi
	else
		echo "Funnel server not running."
	fi

.PHONY: funnel-logs
funnel-logs: $(LOG_DIR)
	touch "$(FUNNEL_LOG)"
	tail -n 200 -f "$(FUNNEL_LOG)"

.PHONY: funnel-kill-port
funnel-kill-port:
	@if ! command -v lsof >/dev/null 2>&1; then \
		echo "lsof is required for this operation."; \
		exit 1; \
	fi
	port_pids=$$(lsof -ti:$(FUNNEL_PORT) 2>/dev/null | tr '\n' ' ')
	if [ -z "$$port_pids" ]; then
		echo "No processes found using port $(FUNNEL_PORT)."
	else
		echo "Processes using port $(FUNNEL_PORT): $$port_pids"
		read -rp "Kill these processes? [y/N]: " confirm
		case $$confirm in \
			y|Y) \
				for pid in $$port_pids; do \
					if ps -p $$pid >/dev/null 2>&1; then \
						kill $$pid || true; \
					fi; \
				done; \
				rm -f "$(FUNNEL_PID)"; \
				echo "Attempted to kill: $$port_pids"; \
				;; \
			*) \
				echo "Aborted."; \
				exit 1; \
				;; \
		esac
	fi

.PHONY: funnel-push
funnel-push: check-git ensure-funnel-dir
	if [ ! -d "$(FUNNEL_DIR)/.git" ]; then
		echo "$(FUNNEL_DIR) is not a git repository."
		exit 1
	fi
	cd "$(FUNNEL_DIR)"
	git status --short
	read -rp "Commit message for funnel: " msg
	if [ -z "$$msg" ]; then
		echo "Commit message cannot be empty."
		exit 1
	fi
	git add -A
	if git diff --cached --quiet; then
		echo "No staged changes to commit."
		exit 0
	fi
	git commit -m "$$msg"
	git push

.PHONY: api-install
api-install: check-python $(PYTHON_BIN) ensure-api-dir
	cd "$(API_DIR)"
	$(PIP_BIN) install -r requirements.txt

.PHONY: api-start
api-start: check-python ensure-api-dir $(PID_DIR) $(LOG_DIR)
	if [ ! -x "$(UVICORN_BIN)" ]; then
		echo "Missing $(UVICORN_BIN). Run 'make api-install' first."
		exit 1
	fi
	if [ -f "$(API_PID)" ] && ps -p $$(cat "$(API_PID)") >/dev/null 2>&1; then
		echo "API already running (PID $$(cat "$(API_PID)"))."
	else
		if command -v lsof >/dev/null 2>&1; then \
			port_pids=$$(lsof -ti:$(API_PORT) 2>/dev/null | tr '\n' ' '); \
			if [ -n "$$port_pids" ]; then \
				echo "Port $(API_PORT) is already in use by: $$port_pids"; \
				echo "Stop the listed process or run with API_PORT=<port> make api-start."; \
				exit 1; \
			fi; \
		fi
		cd "$(API_DIR)"
		echo "Starting FastAPI server on $(API_HOST):$(API_PORT)..."
		nohup "$(UVICORN_BIN)" $(API_APP) --reload --host $(API_HOST) --port $(API_PORT) >> "$(API_LOG_ABS)" 2>&1 &
		new_pid=$$!
		sleep 1
		if ps -p $$new_pid >/dev/null 2>&1; then
			echo $$new_pid > "$(API_PID_ABS)"
			echo "API server started (PID $$new_pid). Logs: $(API_LOG_ABS)"
		else
			echo "API failed to start. See recent logs below:"
			tail -n 40 "$(API_LOG_ABS)" || true
			rm -f "$(API_PID)"
			exit 1
		fi
	fi

.PHONY: api-start-custom
api-start-custom:
	@read -rp "Enter API port (default $(API_PORT)): " custom_port; \
	custom_port=$${custom_port:-$(API_PORT)}; \
	if ! [[ $$custom_port =~ ^[0-9]+$$ ]]; then \
		echo "Port must be numeric."; \
		exit 1; \
	fi; \
	$(MAKE) --no-print-directory API_PORT=$$custom_port api-start

.PHONY: api-stop
api-stop:
	if [ -f "$(API_PID)" ]; then
		pid=$$(cat "$(API_PID)")
		if ps -p $$pid >/dev/null 2>&1; then
			kill $$pid
			echo "Stopped API process $$pid."
		else
			echo "API PID $$pid is stale."
		fi
		rm -f "$(API_PID)"
	else
		echo "API server is not running."
	fi

.PHONY: api-restart
api-restart:
	$(MAKE) api-stop
	$(MAKE) api-start

.PHONY: api-lint
api-lint: $(PYTHON_BIN) ensure-api-dir
	cd "$(API_DIR)"
	$(PYTHON_BIN) -m compileall app backend

.PHONY: api-status
api-status:
	if [ -f "$(API_PID)" ]; then
		pid=$$(cat "$(API_PID)")
		if ps -p $$pid >/dev/null 2>&1; then
			echo "API running (PID $$pid) on $(API_HOST):$(API_PORT)."
		else
			echo "API PID file exists but process $$pid is not running."
			rm -f "$(API_PID)"
		fi
	else
		echo "API server not running."
	fi

.PHONY: api-logs
api-logs: $(LOG_DIR)
	touch "$(API_LOG)"
	tail -n 200 -f "$(API_LOG)"

.PHONY: api-kill-port
api-kill-port:
	@if ! command -v lsof >/dev/null 2>&1; then \
		echo "lsof is required for this operation."; \
		exit 1; \
	fi
	port_pids=$$(lsof -ti:$(API_PORT) 2>/dev/null | tr '\n' ' ')
	if [ -z "$$port_pids" ]; then
		echo "No processes found using port $(API_PORT)."
	else
		echo "Processes using port $(API_PORT): $$port_pids"
		read -rp "Kill these processes? [y/N]: " confirm
		case $$confirm in \
			y|Y) \
				for pid in $$port_pids; do \
					if ps -p $$pid >/dev/null 2>&1; then \
						kill $$pid || true; \
					fi; \
				done; \
				rm -f "$(API_PID)"; \
				echo "Attempted to kill: $$port_pids"; \
				;; \
			*) \
				echo "Aborted."; \
				exit 1; \
				;; \
		esac
	fi

.PHONY: api-migrate
api-migrate: ensure-api-dir
	if [ ! -x "$(ALEMBIC_BIN)" ]; then
		echo "Alembic not found at $(ALEMBIC_BIN). Run 'make api-install' first."
		exit 1
	fi
	cd "$(API_DIR)"
	"$(ALEMBIC_BIN)" upgrade head

.PHONY: api-push
api-push: check-git ensure-api-dir
	if [ ! -d "$(API_DIR)/.git" ]; then
		echo "$(API_DIR) is not a git repository."
		exit 1
	fi
	cd "$(API_DIR)"
	git status --short
	read -rp "Commit message for API: " msg
	if [ -z "$$msg" ]; then
		echo "Commit message cannot be empty."
		exit 1
	fi
	git add -A
	if git diff --cached --quiet; then
		echo "No staged changes to commit."
		exit 0
	fi
	git commit -m "$$msg"
	git push
