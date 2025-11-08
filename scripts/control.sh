#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -gt 0 ]]; then
  (cd "$ROOT_DIR" && make "$@")
  exit $?
fi

if [[ ! -t 0 ]]; then
  echo "Interactive Control Center requires a TTY. Run 'make target-list' or specific targets instead."
  exit 1
fi

trap 'echo; echo "Exiting control center."; exit 0' INT

pause() {
  if [[ -t 0 ]]; then
    read -rp "Press Enter to continue..." _ || true
  fi
}

run_make() {
  local target="$1"
  shift || true
  if (cd "$ROOT_DIR" && make -s "$target" "$@"); then
    echo ""
    echo "[✓] $target completed."
    sleep 0.1
    return 0
  else
    local status=$?
    echo ""
    echo "[✗] $target failed (exit $status). See above for details."
    pause
    return $status
  fi
}

funnel_menu() {
  while true; do
    cat <<EOF
------------------------------------------------------
  Funnel Commands
------------------------------------------------------
  1) Install dependencies
  2) Start dev server
  3) Stop dev server
  4) Restart dev server
  5) Build production bundle
  6) Run lint checks
  7) Show status
  8) Tail logs
  9) Push to git
 10) Start dev server (custom port)
 11) Force-kill funnel port
  0) Back
------------------------------------------------------
EOF
    read -rp "Select a funnel action: " choice
    case "$choice" in
      1) run_make funnel-install ;;
      2) run_make funnel-start ;;
      3) run_make funnel-stop ;;
      4) run_make funnel-restart ;;
      5) run_make funnel-build ;;
      6) run_make funnel-lint ;;
      7) run_make funnel-status ;;
      8) (cd "$ROOT_DIR" && make funnel-logs) ;;
      9) run_make funnel-push ;;
      10) run_make funnel-start-custom ;;
      11) run_make funnel-kill-port ;;
      0|"") break ;;
      *) echo "Invalid choice." ;;
    esac
  done
}

api_menu() {
  while true; do
    cat <<EOF
------------------------------------------------------
  API Commands
------------------------------------------------------
  1) Install dependencies
  2) Start server
  3) Stop server
  4) Restart server
  5) Run lint (compileall)
  6) Show status
  7) Tail logs
  8) Run migrations
  9) Push to git
 10) Start server (custom port)
 11) Force-kill API port
  0) Back
------------------------------------------------------
EOF
    read -rp "Select an API action: " choice
    case "$choice" in
      1) run_make api-install ;;
      2) run_make api-start ;;
      3) run_make api-stop ;;
      4) run_make api-restart ;;
      5) run_make api-lint ;;
      6) run_make api-status ;;
      7) (cd "$ROOT_DIR" && make api-logs) ;;
      8) run_make api-migrate ;;
      9) run_make api-push ;;
      10) run_make api-start-custom ;;
      11) run_make api-kill-port ;;
      0|"") break ;;
      *) echo "Invalid choice." ;;
    esac
  done
}

utilities_menu() {
  while true; do
    cat <<EOF
------------------------------------------------------
  Utilities / Global Actions
------------------------------------------------------
  1) Setup everything (deps + venvs)
  2) Start funnel + API
  3) Stop funnel + API
  4) Restart both services
  5) Status summary
  6) Diagnostics (ports + log tails)
  0) Back
------------------------------------------------------
EOF
    read -rp "Select a utility action: " choice
    case "$choice" in
      1) run_make setup-all ;;
      2) run_make start-all ;;
      3) run_make stop-all ;;
      4) run_make restart-all ;;
      5) run_make status-all ;;
      6) run_make diagnostics ;;
      0|"") break ;;
      *) echo "Invalid choice." ;;
    esac
  done
}

while true; do
  cat <<EOF
======================================================
   SacredFlow Control Center
======================================================
  1) Funnel commands
  2) API commands
  3) Utilities / Global actions
  4) Show target list
  0) Exit
------------------------------------------------------
EOF
  read -rp "Choose an option: " choice
  case "$choice" in
    1) funnel_menu ;;
    2) api_menu ;;
    3) utilities_menu ;;
    4) (cd "$ROOT_DIR" && make -s target-list) ;;
    0|"") echo "Goodbye!"; exit 0 ;;
    *) echo "Invalid option." ;;
  esac
done
