# app.py
from flask import Flask, request, jsonify, abort, render_template_string
from openai import OpenAI
from flask_cors import CORS
import sqlite3, os


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Mini Tweets</title>
  <style>
    body{font-family:system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; max-width:700px; margin:40px auto; padding:0 16px;}
    h1{font-size:1.5rem;}
    .card{border:1px solid #ddd; border-radius:12px; padding:12px; margin:10px 0;}
    small{color:#666;}
    #list{margin-top:20px;}
    input, textarea, button{font:inherit; padding:10px; border:1px solid #ccc; border-radius:8px;}
    button{cursor:pointer;}
    form{display:grid; gap:10px; grid-template-columns:1fr auto;}
    textarea{grid-column:1 / -1; resize:vertical; min-height:60px;}
  </style>
</head>
<body>
  <h1>Mini Tweets</h1>
  <form id="postForm">
    <input id="author" name="author" placeholder="Your name" maxlength="50" required>
    <button type="submit">Post</button>
    <textarea id="text" name="text" placeholder="What's happening?" maxlength="280" required></textarea>
  </form>
  <div id="list"></div>

  <script>
    async function fetchTweets(){
      const res = await fetch('/api/tweets');
      const data = await res.json();
      const list = document.getElementById('list');
      list.innerHTML = '';
      data.forEach(t => {
        const card = document.createElement('div');
        card.className = 'card';
        const author = document.createElement('strong');
        author.textContent = t.author; // safe: textContent escapes
        const text = document.createElement('p');
        text.textContent = t.text;
        const meta = document.createElement('small');
        // SQLite CURRENT_TIMESTAMP is UTC without 'Z'; append Z for Date parsing
        meta.textContent = new Date(t.created_at + 'Z').toLocaleString();
        card.append(author, document.createElement('br'), text, meta);
        list.appendChild(card);
      });
    }

    document.getElementById('postForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const author = document.getElementById('author').value.trim();
      const text   = document.getElementById('text').value.trim();
      if(!author || !text) return;

      const res = await fetch('/api/tweets', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({author, text})
      });

      if(res.ok){
        document.getElementById('text').value = '';
        await fetchTweets();
      } else {
        const err = await res.json().catch(() => ({error:'Unknown error'}));
        alert(err.error || 'Error');
      }
    });

    fetchTweets();
  </script>
</body>
</html>"""



app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
DB_PATH = os.environ.get('DB_PATH', 'tweets.db')


# --- Configure OpenAI client ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") or "")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_db():
    conn = get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tweets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT NOT NULL,
                text   TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()

create_db()

@app.get('/api/tweets')
def list_tweets():
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, author, text, created_at FROM tweets ORDER BY id DESC LIMIT 100"
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.post('/api/tweets')
def create_tweet():
    data = request.get_json(silent=True) or {}
    author = (data.get('author') or '').strip()
    text   = (data.get('text') or '').strip()

    if not author or not text:
        return jsonify({"error": "author and text are required"}), 400
    if len(author) > 50 or len(text) > 280:
        return jsonify({"error": "author<=50, text<=280"}), 400

    conn = get_conn()
    try:
        cur = conn.execute("INSERT INTO tweets (author, text) VALUES (?, ?)", (author, text))
        conn.commit()
        tweet_id = cur.lastrowid
        row = conn.execute("SELECT id, author, text, created_at FROM tweets WHERE id=?", (tweet_id,)).fetchone()
        return jsonify(dict(row)), 201
    finally:
        conn.close()

# --- UI ---
@app.get("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/chat", methods=["POST"])
def chat():

    # 2️⃣  Parse payload
    data = request.get_json(force=True)
    if "messages" in data:
        messages = data["messages"]                         # already role-tagged
    elif "prompt" in data:
        messages = [{"role": "user", "content": data["prompt"]}]
    else:
        abort(400, description="JSON must include 'prompt' or 'messages'")

    # 3️⃣  Forward to OpenAI
    try:
        resp = client.chat.completions.create(
            model=data.get("model", "gpt-4o"),              # default model
            messages=messages,
            temperature=data.get("temperature", 0.7),
        )
        answer = resp.choices[0].message.content
        return jsonify({"answer": answer}), 200
    except Exception as exc:
        abort(500, description=f"OpenAI error: {exc}")

@app.route("/ask", methods=["GET"])
def get():
    return jsonify("Hello World")

# --- Dev entry-point ---
if __name__ == "__main__":
    # 0.0.0.0 so it works in containers / render.com
    app.run(host="0.0.0.0", port=5001, debug=True)
