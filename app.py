# app.py
from flask import Flask, request, jsonify, abort
from openai import OpenAI
from flask_cors import CORS
import os


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


# --- Configure OpenAI client ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
