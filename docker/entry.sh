#!/bin/bash
set -e

CONFIG_FILE="/app/data/config.ini"

# 如果 config.ini 不存在，创建默认配置
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating default config.ini..."
    cat > "$CONFIG_FILE" << 'CONFEOF'
[download]
# 本地开发: http://localhost:3000 | Docker Compose: http://javbus-api:3000 | 自部署: 你的域名
api_base_url = http://localhost:3000
auth_token = 
javbus_url = https://www.javbus.com
img_base_url = https://www.javbus.com
count = 10
magnet = exist
movie_type = normal,uncensored
# 定时模式：指定每天执行时间点（北京时间），留空则用 interval 间隔模式
schedule = 8:00,12:00,15:00,22:00
# 间隔模式：仅当 schedule 为空时生效（10800秒=3小时, 3600秒=1小时）
interval = 10800
api_interval = 0.5
batch_size = 100
batch_interval = 5
img_cache_enabled = true
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

if [ -n "$JAVBUS_URL" ]; then
    sed -i "s|javbus_url = .*|javbus_url = $JAVBUS_URL|g" "$CONFIG_FILE"
    echo "Configured javbus_url: $JAVBUS_URL"
fi

if [ -n "$JAVBUS_IMG_URL" ]; then
    sed -i "s|img_base_url = .*|img_base_url = $JAVBUS_IMG_URL|g" "$CONFIG_FILE"
    echo "Configured img_base_url: $JAVBUS_IMG_URL"
fi

echo "Starting supervisord..."
/usr/bin/supervisord -c /etc/supervisor/supervisord.conf &

# 等待服务启动
echo "Warming up services..."
sleep 3

# 预热：触发 API 加载，让图片缓存开始填充
for i in 1 2 3; do
  if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/index 2>/dev/null | grep -q "200"; then
    echo "Backend is ready, preloading data..."
    curl -s http://127.0.0.1:8000/api/index > /dev/null 2>&1 &
    curl -s http://127.0.0.1:8000/api/tagit > /dev/null 2>&1 &
    break
  fi
  echo "Waiting for backend... (attempt $i)"
  sleep 2
done

# 保持容器运行
wait
