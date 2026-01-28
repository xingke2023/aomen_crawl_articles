# Aomen Article Crawl - Flask API

澳门文章爬虫系统的Flask API服务

## 数据库配置

- **主机**: localhost
- **端口**: 8510
- **用户**: root
- **密码**: Uu8297636
- **数据库名**: aomen_article_crawl

## 安装依赖

```bash
pip install -r requirements.txt
```

## 初始化数据库

```bash
python init_db.py
```

## 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5916` 启动

## API 端点

### 基础端点

- `GET /` - 欢迎页面
- `GET /health` - 健康检查（包含数据库连接状态）

### 文章管理

- `GET /articles` - 获取所有文章
- `POST /articles` - 创建新文章
- `GET /articles/<id>` - 获取指定文章

### 创建文章示例

```bash
curl -X POST http://localhost:5916/articles \
  -H "Content-Type: application/json" \
  -d '{
    "title": "示例文章标题",
    "link": "https://example.com/article/123",
    "content": "这是文章的详细内容...",
    "publish_time": "2026-01-10 15:30:00"
  }'
```

## 数据库表结构

### articles 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键，自增 |
| title | VARCHAR(500) | 文章标题 |
| link | VARCHAR(1000) | 文章链接 |
| content | TEXT | 文章内容 |
| publish_time | DATETIME | 文章发布时间 |
| created_at | DATETIME | 记录创建时间 |
