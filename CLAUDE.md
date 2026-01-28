# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an article crawling and management system for collecting articles from multiple Chinese websites (kknews.cc for Macau-related content, gangbaobaohk.com for Hong Kong insurance articles). The system consists of web crawlers that store articles in MySQL and a Flask API/web interface for viewing and managing the content.

## Database Configuration

All scripts connect to MySQL on a non-standard port:
- Host: `localhost`
- Port: `8510` (not 3306)
- Database: `aomen_article_crawl`
- User/Password: See `config.py` or individual crawler files

The `articles` table schema:
- `id`, `title`, `link` (unique)
- `source` (来源), `tags` (标签) - for categorization
- `content` (longtext), `publish_time`, `created_at`
- `is_parsed` (tinyint)

## Running the Application

### Flask Web Interface
```bash
python app.py
# Runs on http://localhost:5916
```

### Database Initialization
```bash
python init_db.py              # Initialize database
python update_table_add_fields.py  # Add source/tags fields
```

### View Statistics
```bash
python check_articles_stats.py  # Show article counts by source/tags
```

## Crawler Architecture

The project has two main crawler families:

### 1. kknews.cc Crawler (Macau Content)
**Primary file**: `auto_crawler1.py`

- Source identifier: `kknews`
- Tags: `澳门`
- Uses **Playwright** for JavaScript-rendered pages (Google Custom Search results)
- Integrates **1024proxy** for IP rotation (credentials in script)
- Crawls from search result URLs, automatically handles pagination

**Usage**:
```bash
python auto_crawler1.py '<search_results_URL>' [max_pages]
# Example: python auto_crawler1.py 'https://kknews.cc/search/?q=澳门#gsc.tab=0&gsc.q=澳门&gsc.page=1' 10
```

**Key features**:
- Parses Google Custom Search result pages
- Extracts article links matching kknews.cc domain
- Fetches full article content using cloudscraper (bypasses Cloudflare)
- Auto-retry on failure (up to 3 times)
- Delay ranges: PAGE_DELAY_RANGE=(2,4), ARTICLE_DELAY_RANGE=(1,3)

### 2. gangbaobaohk.com Crawler (Hong Kong Insurance)
**Primary files**:
- `gangbaobao_crawler_v2.py` - Single-run version
- `gangbaobao_crawler_loop.py` - Smart loop with pagination
- `gangbaobao_crawler_infinite.py` - Infinite monitoring loop

- Source identifier: `港保保`
- Tags: `香港保险`
- Uses **Playwright** with SSL verification disabled (site certificate expired)
- Targets article pages matching pattern `/h-nd-\d+\.html`

**Usage**:
```bash
# Single run (limited articles)
python gangbaobao_crawler_v2.py http://gangbaobaohk.com/ 50

# Smart loop (auto-stops after 10 consecutive duplicates)
python gangbaobao_crawler_loop.py http://gangbaobaohk.com/ [max_articles]

# Infinite monitoring (runs forever, periodic scans)
python gangbaobao_crawler_infinite.py
```

**Key architecture**:
- `get_page_content()` - Playwright wrapper with SSL bypass
- `parse_article_list()` - Extracts article links using regex
- `parse_article_content()` - Finds content via multiple selector fallbacks + largest text block heuristic
- Loop version tracks visited URLs and pagination links
- Infinite version runs in rounds with 3-10 minute intervals

## Deduplication Strategy

All crawlers check before inserting:
```sql
SELECT id, content FROM articles
WHERE link = %s OR (title = %s AND source = %s)
```

- If exists with content: skip
- If exists without content: update with new content
- Otherwise: insert new record

## Content Cleaning Utilities

- `remove_facebook_line.py` - Remove Facebook-related lines
- `remove_extra_blank_lines.py` - Clean excessive whitespace
- `remove_dot_pattern.py` - Remove pattern-based noise characters

These operate directly on the database `content` field.

## Adding New Crawlers

Template: Copy `gangbaobao_crawler_v2.py` and modify:
1. Update `SOURCE` and `TAGS` constants
2. Adjust URL patterns in `parse_article_list()` (change regex)
3. Modify content selectors in `parse_article_content()` for target site's HTML structure
4. Test with small batch first (limit to 5-10 articles)

## Anti-Scraping Measures

- **kknews crawler**: Uses 1024proxy with rotating IPs
- **gangbaobao crawler**: Random delays + headless Playwright
- Both: Realistic User-Agent headers
- Both: Exponential backoff on retries
- Adjust `PAGE_DELAY_RANGE` and `ARTICLE_DELAY_RANGE` if getting blocked

## Important Notes

- The Flask app uses SQLAlchemy ORM, but crawlers use raw PyMySQL for direct SQL
- Playwright requires `python -m playwright install chromium` after pip install
- gangbaobaohk.com has expired SSL cert - all requests use `verify=False` or `ignore_https_errors=True`
- Loop crawlers stop when encountering `MAX_CONSECUTIVE_DUPLICATES` (default: 10) repeated articles
- Database credentials are hardcoded in scripts (not using .env or config.py consistently)

## Testing

```bash
# Test crawler on small dataset
python gangbaobao_crawler_v2.py http://gangbaobaohk.com/ 5

# Check if articles were saved
python check_articles_stats.py

# View in browser
python app.py  # Then visit http://localhost:5916
```

## Background Execution

For long-running crawlers:
```bash
# Using screen (recommended)
screen -S crawler
python gangbaobao_crawler_infinite.py
# Ctrl+A then D to detach

# Using nohup
nohup python gangbaobao_crawler_loop.py http://gangbaobaohk.com/ > crawler.log 2>&1 &
```
