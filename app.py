# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/ask", methods=["GET"])
def get():
    return jsonify("Hello World")
