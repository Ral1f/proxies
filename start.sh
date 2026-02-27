#!/bin/bash

SCREEN_NAME="proxies"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Проверяем, не запущен ли уже
if screen -ls | grep -q "\.$SCREEN_NAME\b"; then
    echo "Screen '$SCREEN_NAME' уже запущен"
    exit 1
fi

screen -dmS "$SCREEN_NAME"
screen -S "$SCREEN_NAME" -X stuff "cd $SCRIPT_DIR\n"
screen -S "$SCREEN_NAME" -X stuff "python3 -m proxy_pipeline.updater --interval-seconds 300 --deactivate-missing\n"

echo "Screen '$SCREEN_NAME' запущен"
