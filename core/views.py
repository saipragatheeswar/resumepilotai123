import requests
import json
from django.shortcuts import render, redirect
from PyPDF2 import PdfReader


def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""

    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    return text


import ollama
import json
import re

def analyze_resume_with_ollama(resume_text):
    prompt = f"""
You are an ATS Resume Scoring AI.

Return ONLY valid JSON in this format:

{{
    "ats_score": 0,
    "improvements": [
        "Improvement 1",
        "Improvement 2",
        "Improvement 3"
    ],
    "feedback": "Overall feedback"
}}

Resume:
{resume_text}
"""

    try:
        response = ollama.chat(
            model="mistral",
            messages=[
                {"role": "system", "content": "You must return only valid JSON. No extra text."},
                {"role": "user", "content": prompt}
            ]
        )

        raw_output = response["message"]["content"].strip()
        print("RAW OUTPUT:", raw_output)

        # 🔥 Extract JSON using regex
        json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)

        if not json_match:
            raise ValueError("No valid JSON found")

        clean_json = json_match.group()

        return json.loads(clean_json)

    except Exception as e:
        print("ERROR:", str(e))
        return {
            "ats_score": "Error",
            "improvements": ["Model returned invalid JSON."],
            "feedback": "Please try again."
        }

def home(request):
    if request.method == "POST" and request.FILES.get("resume"):
        resume_file = request.FILES["resume"]

        resume_text = extract_text_from_pdf(resume_file)

        analysis = analyze_resume_with_ollama(resume_text)

        # Store in session
        request.session["analysis"] = analysis

        return redirect("result")

    return render(request, "home.html")


def result(request):
    analysis = request.session.get("analysis")

    if not analysis:
        return redirect("home")

    return render(request, "result.html", {"analysis": analysis})

import ollama
from django.shortcuts import render
from django.http import JsonResponse



def interview_chat(request):

    # If AJAX POST request
    if request.method == "POST":
        user_input = request.POST.get("question")

        # Only send current message (no history)
        response = ollama.chat(
            model="llama3.2",
            messages=[
                {"role": "system", "content": "You are an expert technical interviewer."},
                {"role": "user", "content": user_input}
            ]
        )

        bot_reply = response["message"]["content"]

        return JsonResponse({"reply": bot_reply})

    # For GET request (fresh page)
    return render(request, "interview.html", {
        "messages": []   # Always empty
    })