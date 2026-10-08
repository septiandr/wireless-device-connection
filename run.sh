#!/bin/bash
# Script serbaguna satu pintu
cd "$(dirname "$0")"

case "$1" in
  cli)
    python3 main.py --cli
    ;;
  mirror|scrcpy)
    python3 main.py --scrcpy
    ;;
  send|push)
    shift
    python3 main.py --send "$@"
    ;;
  get|pull)
    shift
    python3 main.py --get "$@"
    ;;
  ls)
    shift
    python3 main.py --ls "$@"
    ;;
  devices|dev)
    python3 main.py --devices
    ;;
  *)
    # Default: buka Web Dashboard
    python3 main.py
    ;;
esac
