#!/bin/bash
set -e

CONFIG_FILE="/app/data/config.ini"

# 如果 config.ini 不存在，创建默认配置
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating default config.ini..."
    cat > "$CONFIG_FILE" << 'CONFEOF'
[download]
api_base_url = http://localhost:3000
auth_token = 
count = 10
interval = 10800
CONFEOF
fi

# 支持通过环境变量配置 javbus-api 地址
if [ -n "$JAVBUS_API_URL" ]; then
    sed -i "s|api_base_url = .*|api_base_url = $JAVBUS_API_URL|g" "$CONFIG_FILE"
    echo "Configured api_base_url: $JAVBUS_API_URL"
fi

if [ -n "$JAVBUS_AUTH_TOKEN" ]; then
    sed -i "s|auth_token = .*|auth_token = $JAVBUS_AUTH_TOKEN|g" "$CONFIG_FILE"
    echo "Configured auth_token"
fi

echo "Starting bustag server..."
exec python3 -m bustag.app.index