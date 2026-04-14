#!/bin/bash
set -e

# 支持通过环境变量配置 javbus-api 地址
if [ -n "$JAVBUS_API_URL" ]; then
    sed -i "s|api_base_url = .*|api_base_url = $JAVBUS_API_URL|g" /app/data/config.ini
    echo "Configured api_base_url: $JAVBUS_API_URL"
fi

if [ -n "$JAVBUS_AUTH_TOKEN" ]; then
    sed -i "s|auth_token = .*|auth_token = $JAVBUS_AUTH_TOKEN|g" /app/data/config.ini
    echo "Configured auth_token"
fi

echo "Starting bustag server..."
exec python3 -m bustag.app.index