from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Uu8297636@localhost:8510/aomen_article_crawl'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

db = SQLAlchemy(app)

# 文章表模型
class Article(db.Model):
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(500), nullable=False, comment='文章标题')
    link = db.Column(db.String(1000), nullable=False, comment='文章链接')
    content = db.Column(db.Text, comment='文章内容')
    publish_time = db.Column(db.DateTime, comment='文章发布时间')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'link': self.link,
            'content': self.content,
            'publish_time': self.publish_time.isoformat() if self.publish_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# 路由
@app.route('/')
def index():
    try:
        page = request.args.get('page', 1, type=int)
        search_query = request.args.get('search', '', type=str).strip()
        per_page = 20  # 每页显示20条

        # 构建查询
        query = Article.query

        # 如果有搜索关键词，添加搜索条件
        if search_query:
            search_pattern = f'%{search_query}%'
            query = query.filter(
                db.or_(
                    Article.title.like(search_pattern),
                    Article.content.like(search_pattern)
                )
            )

        # 排序和分页
        pagination = query.order_by(Article.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return render_template('articles.html',
                             articles=pagination.items,
                             pagination=pagination,
                             search_query=search_query)
    except Exception as e:
        return render_template('articles.html', articles=[], pagination=None, error=str(e), search_query='')

@app.route('/health')
def health():
    try:
        # 测试数据库连接
        db.session.execute(db.text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 500

@app.route('/articles', methods=['GET'])
def get_articles():
    try:
        articles = Article.query.all()
        return jsonify({
            'success': True,
            'count': len(articles),
            'data': [article.to_dict() for article in articles]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/articles', methods=['POST'])
def create_article():
    try:
        data = request.get_json()

        # 处理时间字段
        publish_time = None
        if data.get('publish_time'):
            from dateutil import parser
            publish_time = parser.parse(data.get('publish_time'))

        article = Article(
            title=data.get('title'),
            link=data.get('link'),
            content=data.get('content'),
            publish_time=publish_time
        )

        db.session.add(article)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Article created successfully',
            'data': article.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/article/<int:article_id>')
def view_article(article_id):
    try:
        article = Article.query.get(article_id)
        return render_template('article_detail.html', article=article)
    except Exception as e:
        return render_template('article_detail.html', article=None, error=str(e))

@app.route('/api/articles/<int:article_id>', methods=['GET'])
def get_article(article_id):
    try:
        article = Article.query.get(article_id)
        if not article:
            return jsonify({
                'success': False,
                'error': 'Article not found'
            }), 404

        return jsonify({
            'success': True,
            'data': article.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5916, debug=True)
