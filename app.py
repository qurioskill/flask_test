# app.py
from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)
openai.api_key = os.environ["OPENAI_API_KEY"]

@app.route("/ask", methods=["GET"])
def get():
    return jsonify("Hello World")
