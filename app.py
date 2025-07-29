# app.py
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/ask", methods=["GET"])
def get():
    return jsonify("Hello World")
