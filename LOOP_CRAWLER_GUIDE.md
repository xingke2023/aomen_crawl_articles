# 循环爬虫使用指南

## 三种爬虫模式对比

### 1. **单次爬取** - `gangbaobao_crawler_v2.py`
适合：测试、少量抓取
```bash
# 抓取 50 篇后停止
python gangbaobao_crawler_v2.py http://gangbaobaohk.com/ 50
```

### 2. **智能循环** - `gangbaobao_crawler_loop.py` ⭐ 推荐
适合：大量抓取，自动翻页，智能停止
```bash
# 抓取 500 篇后停止
python gangbaobao_crawler_loop.py http://gangbaobaohk.com/ 500

# 无限抓取，直到没有新文章
python gangbaobao_crawler_loop.py http://gangbaobaohk.com/
```

**特点**：
- ✅ 自动查找并访问分页链接
- ✅ 连续遇到 10 篇重复文章自动停止
- ✅ 智能去重
- ✅ 支持设置最大文章数或无限制
- ✅ 实时统计进度

### 3. **无限循环** - `gangbaobao_crawler_infinite.py`
适合：7x24 持续监控，抓取更新
```bash
# 一直运行，定期扫描新文章
python gangbaobao_crawler_infinite.py
```

**特点**：
- ✅ 无限循环扫描
- ✅ 每轮结束后等待 3-10 分钟
- ✅ 如果没有新文章，等待 10 分钟重试
- ✅ 可以用 Ctrl+C 随时停止
- ✅ 适合放在后台运行

---

## 🚀 快速开始

### 方式1: 一次性抓取所有（推荐）
```bash
# 自动抓取所有文章，遇到 10 篇连续重复后停止
python gangbaobao_crawler_loop.py http://gangbaobaohk.com/
```

### 方式2: 限制数量
```bash
# 只抓取 100 篇
python gangbaobao_crawler_loop.py http://gangbaobaohk.com/ 100
```

### 方式3: 后台持续运行
```bash
# 使用 nohup 在后台运行
nohup python gangbaobao_crawler_infinite.py > gangbaobao.log 2>&1 &

# 查看日志
tail -f gangbaobao.log

# 停止后台任务
ps aux | grep gangbaobao_crawler_infinite
kill <进程ID>
```

### 方式4: 使用 screen（推荐后台运行）
```bash
# 创建新会话
screen -S gangbaobao

# 运行爬虫
python gangbaobao_crawler_infinite.py

# 按 Ctrl+A 然后按 D 分离会话

# 重新连接
screen -r gangbaobao

# 查看所有会话
screen -ls
```

---

## 📊 实时监控

### 查看抓取进度
```bash
# 实时查看统计
watch -n 5 python check_articles_stats.py

# 或者每 10 秒查询一次
while true; do
  clear
  python check_articles_stats.py
  sleep 10
done
```

### 查看数据库最新文章
```python
# 创建监控脚本
cat > monitor.py << 'EOF'
import pymysql
from datetime import datetime

conn = pymysql.connect(
    host='localhost', port=8510,
    user='root', password='Uu8297636',
    database='aomen_article_crawl'
)
cur = conn.cursor()

while True:
    cur.execute("""
        SELECT COUNT(*) FROM articles WHERE source = '港保保'
    """)
    count = cur.fetchone()[0]

    cur.execute("""
        SELECT title, created_at FROM articles
        WHERE source = '港保保'
        ORDER BY created_at DESC LIMIT 1
    """)
    latest = cur.fetchone()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 港保保文章: {count} 篇")
    if latest:
        print(f"  最新: {latest[0][:50]} ({latest[1]})")

    import time
    time.sleep(10)
EOF

python monitor.py
```

---

## ⚙️ 配置说明

### 修改延时（避免被封）
编辑爬虫文件，修改这些参数：

```python
# 页面间延时（秒）
PAGE_DELAY_RANGE = (3, 6)  # 改成 (5, 10) 更安全

# 文章间延时（秒）
ARTICLE_DELAY_RANGE = (1, 3)  # 改成 (2, 5) 更安全

# 连续重复文章阈值
MAX_CONSECUTIVE_DUPLICATES = 10  # 改成 20 更宽容
```

### 修改超时时间
```python
# Playwright 页面加载超时（毫秒）
page.goto(url, timeout=30000)  # 改成 60000 (60秒)
```

---

## 🛠️ 常见问题

### Q: 如何知道爬虫是否还在运行？
```bash
# 查看进程
ps aux | grep gangbaobao

# 查看最新文章时间
python check_articles_stats.py
```

### Q: 爬虫卡住不动了怎么办？
```bash
# 找到进程ID
ps aux | grep gangbaobao

# 强制停止
kill -9 <进程ID>

# 重新启动
python gangbaobao_crawler_loop.py http://gangbaobaohk.com/
```

### Q: 如何设置开机自启动？
```bash
# 创建 systemd 服务
sudo nano /etc/systemd/system/gangbaobao-crawler.service
```

内容：
```ini
[Unit]
Description=Gangbaobao Article Crawler
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/var/www/aomen_crawl_articles
ExecStart=/usr/bin/python3 gangbaobao_crawler_infinite.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

然后：
```bash
sudo systemctl daemon-reload
sudo systemctl enable gangbaobao-crawler
sudo systemctl start gangbaobao-crawler
sudo systemctl status gangbaobao-crawler
```

### Q: 如何只抓取特定分类？
修改爬虫脚本中的 URL：
```python
# 如果网站有分类页面，直接使用分类URL
start_url = 'http://gangbaobaohk.com/h-col-111.html'  # 储蓄分红保险
```

---

## 📈 性能建议

### 单台服务器
```bash
# 适中速度，适合长期运行
PAGE_DELAY_RANGE = (3, 6)
ARTICLE_DELAY_RANGE = (1, 3)
```

### 多台服务器/代理
```bash
# 可以加快速度
PAGE_DELAY_RANGE = (1, 2)
ARTICLE_DELAY_RANGE = (0.5, 1.5)
```

### 谨慎模式（避免被封）
```bash
# 慢速但安全
PAGE_DELAY_RANGE = (5, 10)
ARTICLE_DELAY_RANGE = (3, 5)
```

---

## 📝 日志说明

### 符号含义
- `✓` - 成功操作
- `✗` - 失败操作
- `⊙` - 跳过（已存在）
- `→` - 发现链接
- `⏱` - 等待中

### 日志示例
```
[15:08:15] 正在抓取文章: http://...
  ✓ 保存新文章成功 (字数: 3320)

[15:08:29] 正在抓取文章: http://...
  ⊙ 文章已存在，跳过

[15:08:43] 正在抓取文章: http://...
  ✗ 获取页面失败: Timeout
```

---

## 🎯 推荐使用流程

### 第一次抓取（抓取历史文章）
```bash
# 使用智能循环，抓取所有文章
python gangbaobao_crawler_loop.py http://gangbaobaohk.com/
```

### 日常更新（监控新文章）
```bash
# 使用无限循环，定期检查
screen -S gangbaobao
python gangbaobao_crawler_infinite.py
# Ctrl+A D 分离会话
```

### 测试新配置
```bash
# 使用单次模式，限制 5 篇
python gangbaobao_crawler_v2.py http://gangbaobaohk.com/ 5
```

---

*最后更新: 2026-01-26*
