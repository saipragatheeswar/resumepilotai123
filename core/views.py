# views.py
import re
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from PyPDF2 import PdfReader
from groq import Groq
from dotenv import load_dotenv
import os
load_dotenv()
# === Groq client ===
client = Groq(api_key=os.getenv("GROQ"))


# === PDF Extraction ===
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text


# === Groq Completion Helper ===
def groq_chat(prompt, model="llama-3.1-8b-instant", max_tokens=1024):
    """
    Generate text using Groq streaming API
    """
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_completion_tokens=max_tokens,
            top_p=1,
            stream=False,  # we use non-streaming for simplicity in Django views
        )
        # Extract content from first choice
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("Groq ERROR:", str(e))
        return ""


# === Resume Analysis ===
def analyze_resume(resume_text):
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
    output_text = groq_chat(prompt, model="llama-3.1-8b-instant")
    print("RAW OUTPUT:", output_text)

    # Extract JSON using regex
    json_match = re.search(r'\{.*\}', output_text, re.DOTALL)
    if not json_match:
        return {
            "ats_score": "Error",
            "improvements": ["Model returned invalid JSON."],
            "feedback": "Please try again."
        }

    try:
        return json.loads(json_match.group())
    except Exception as e:
        print("JSON ERROR:", str(e))
        return {
            "ats_score": "Error",
            "improvements": ["JSON parsing failed."],
            "feedback": "Please try again."
        }


# === Home / Upload Resume ===
def home(request):
    if request.method == "POST" and request.FILES.get("resume"):
        resume_file = request.FILES["resume"]
        resume_text = extract_text_from_pdf(resume_file)
        analysis = analyze_resume(resume_text)

        request.session["analysis"] = analysis
        return redirect("result")

    return render(request, "home.html")


# === Result Page ===
def result(request):
    analysis = request.session.get("analysis")
    if not analysis:
        return redirect("home")
    return render(request, "result.html", {"analysis": analysis})


# === Interview Chat ===
def interview_chat(request):
    if request.method == "POST":
        user_input = request.POST.get("question")

        prompt = f"""
You are an expert technical interviewer.

Answer concisely and professionally.

User Question: {user_input}
"""

        bot_reply = groq_chat(prompt, model="llama-3.1-8b-instant", max_tokens=300)
        if not bot_reply:
            bot_reply = "Sorry, I couldn't generate a response. Try again."

        return JsonResponse({"reply": bot_reply})

    # GET: fresh page
    return render(request, "interview.html", {"messages": []})