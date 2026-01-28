# 文章爬虫使用指南

本项目包含两个主要的爬虫系统，用于抓取不同来源的文章并存储到数据库。

## 数据库表结构

```
articles 表字段:
- id            : 主键（自增）
- title         : 文章标题
- link          : 文章链接（唯一）
- source        : 来源标识（新增）
- tags          : 文章标签（新增）
- content       : 文章正文内容
- publish_time  : 发布时间
- created_at    : 入库时间
- is_parsed     : 是否已解析
```

## 爬虫 1: kknews.cc 爬虫（澳门相关）

### 文件
- `auto_crawler1.py` - 主爬虫脚本

### 标识信息
- **来源**: `kknews`
- **标签**: `澳门`

### 功能特点
- 支持 Google 自定义搜索结果页面抓取
- 使用 Playwright 处理 JavaScript 动态渲染
- 集成 1024proxy 代理服务（自动轮换IP）
- 自动翻页抓取多页搜索结果
- 智能去重（基于链接和标题）
- 失败自动重试（最多3次）

### 使用方法

```bash
# 基本用法
python auto_crawler1.py '<搜索结果URL>' [最大页数]

# 示例：抓取"赌城不是天堂"搜索结果的前10页
python auto_crawler1.py 'https://kknews.cc/search/?q=赌城不是天堂#gsc.tab=0&gsc.q=赌城不是天堂&gsc.page=1' 10

# 示例：抓取"澳门博彩"搜索结果的前5页
python auto_crawler1.py 'https://kknews.cc/search/?q=澳门博彩#gsc.tab=0&gsc.q=澳门博彩&gsc.page=1' 5
```

### 如何获取搜索结果URL
1. 访问 https://kknews.cc/
2. 在搜索框输入关键词（如"澳门"、"赌场"等）
3. 点击搜索
4. 复制浏览器地址栏的完整URL（包括 # 后面的参数）
5. 使用该URL运行爬虫

---

## 爬虫 2: gangbaobaohk.com 爬虫（香港保险）

### 文件
- `gangbaobao_crawler_v2.py` - 港保保爬虫（推荐使用）
- `gangbaobao_crawler.py` - 旧版本（不推荐）

### 标识信息
- **来源**: `港保保`
- **标签**: `香港保险`

### 功能特点
- 使用 Playwright 处理动态页面
- 自动识别文章详情页（h-nd-数字.html格式）
- 智能内容提取（自动查找最大文本块）
- 忽略 SSL 证书验证（网站证书过期）
- 自动去重
- 随机延时避免反爬

### 使用方法

```bash
# 基本用法
python gangbaobao_crawler_v2.py [网站URL] [最大文章数]

# 示例：抓取首页的前50篇文章
python gangbaobao_crawler_v2.py http://gangbaobaohk.com/ 50

# 示例：抓取首页的前100篇文章
python gangbaobao_crawler_v2.py http://gangbaobaohk.com/ 100

# 默认行为（不带参数）：抓取100篇
python gangbaobao_crawler_v2.py
```

### 注意事项
- 该网站 SSL 证书已过期，爬虫会自动忽略证书验证
- 部分页面可能加载较慢，已设置30秒超时
- 建议分批抓取，避免一次性抓取过多

---

## 辅助工具

### 1. 查看文章统计
```bash
python check_articles_stats.py
```
显示：
- 按来源和标签分组的文章数量
- 最近添加的10篇文章

### 2. 更新已有文章标签
```bash
# 更新 kknews 来源的文章标签为"澳门"
python update_existing_articles_tags.py
```

### 3. 更新数据库表结构
```bash
# 添加 source 和 tags 字段
python update_table_add_fields.py
```

---

## 查看抓取结果

### 方式1: 通过 Flask Web 界面
```bash
# 启动 Flask 应用
python app.py

# 访问浏览器
http://localhost:5916/
```

### 方式2: 通过数据库查询
```bash
# 连接数据库
mysql -h localhost -P 8510 -u root -p

# 切换数据库
USE aomen_article_crawl;

# 查看统计
SELECT source, tags, COUNT(*) FROM articles GROUP BY source, tags;

# 查看最新文章
SELECT title, source, tags, created_at FROM articles ORDER BY created_at DESC LIMIT 10;

# 搜索特定标签的文章
SELECT title, link FROM articles WHERE tags = '香港保险' LIMIT 10;
```

---

## 当前数据统计

| 来源 | 标签 | 数量 |
|------|------|------|
| kknews | 澳门 | 41,004 |
| 港保保 | 香港保险 | 5 |
| **总计** | | **41,009** |

---

## 配置说明

### 数据库配置
```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 8510,
    'user': 'root',
    'password': 'Uu8297636',
    'database': 'aomen_article_crawl'
}
```

### 代理配置（auto_crawler1.py）
```python
PROXY_HOST = 'us.1024proxy.io:3000'
PROXY_USERNAME = 'wk4n3645-region-Rand'
PROXY_PASSWORD = 'tw2fvu8c'
```

### 延时配置
```python
PAGE_DELAY_RANGE = (2, 5)      # 页面间延时（秒）
ARTICLE_DELAY_RANGE = (1, 3)   # 文章间延时（秒）
```

---

## 常见问题

### Q: 爬虫抓取失败怎么办？
A:
- 检查网络连接
- 检查代理是否可用（kknews爬虫）
- 增加重试次数
- 查看错误日志

### Q: 如何避免被封IP？
A:
- kknews爬虫已集成代理服务
- 适当增加延时时间
- 分批次抓取

### Q: 如何添加新的文章来源？
A:
1. 复制 `gangbaobao_crawler_v2.py` 作为模板
2. 修改 `SOURCE` 和 `TAGS` 变量
3. 根据目标网站调整选择器
4. 测试后批量运行

### Q: 数据库中有重复文章吗？
A:
爬虫会自动检查：
- 相同链接的文章会跳过
- 相同标题且相同来源的文章会跳过
- 如果有记录但无内容，会更新内容

---

## 开发依赖

```
cloudscraper
beautifulsoup4
pymysql
playwright
requests
```

安装依赖：
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

---

## 日志说明

爬虫运行时会实时显示：
- ✓ 成功操作
- ✗ 失败操作
- ⊙ 跳过操作
- ⟳ 重试操作

日志包含时间戳，便于追踪抓取进度。

---

## 维护建议

1. **定期备份数据库**
2. **监控代理服务状态**（kknews爬虫）
3. **更新 User-Agent**（避免被识别）
4. **定期检查目标网站结构变化**
5. **清理无效或过时的文章**

---

*最后更新: 2026-01-26*
