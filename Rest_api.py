from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

DB_PATH = "articles.db"

def query_db(sql, args=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql, args)
    rows = [dict(ix) for ix in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/categories")
def list_categories():
    sql = "SELECT DISTINCT category FROM articles ORDER BY category"
    return jsonify(query_db(sql))


@app.get("/api/articles")
def list_articles():
    category = request.args.get("category")
    keyword = request.args.get("q")

    sql = "SELECT id, category, title, url, publish_time FROM articles WHERE 1=1"
    args = []

    if category:
        sql += " AND category = ?"
        args.append(category)

    if keyword:
        sql += " AND (title LIKE ? OR content LIKE ?)"
        args.extend([f"%{keyword}%", f"%{keyword}%"])

    sql += " ORDER BY publish_time DESC LIMIT 2000"

    return jsonify(query_db(sql, args))


@app.get("/api/article/<int:aid>")
def get_article(aid):
    sql = "SELECT * FROM articles WHERE id=?"
    result = query_db(sql, (aid,))
    return jsonify(result[0] if result else {})


if __name__ == "__main__":
    app.run(port=5000, debug=True)