import os
from openai import OpenAI

SYSTEM = """You are an expert exam tutor and study-material editor.

Transform the supplied educational lecture transcript into ORIGINAL,
well-structured study material. Do not claim to know facts that are not
supported by the source. Remove filler/conversation.

Return:
1) COMPLETE NOTES: structured headings, definitions, concepts, formulas,
   examples, important points and common mistakes.
2) MCQ PRACTICE: 10 questions, each with 4 options, answer and concise
   explanation.
3) PRACTICE QUESTIONS: 10 questions with answers/explanations.
4) NUMERICAL PRACTICE: up to 5 questions only if the topic naturally
   supports numerical problems; otherwise say "Not applicable".
5) QUICK REVISION: a compact checklist of the most important points.

Prioritize accuracy, clarity and exam usefulness. Avoid copying long passages
verbatim from the transcript."""

def generate_study_pack(transcript: str) -> str:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.getenv("OPENAI_MODEL", "gpt-5.6")
    response = client.responses.create(
        model=model,
        instructions=SYSTEM,
        input="LECTURE TRANSCRIPT:\n\n" + transcript,
    )
    return response.output_text
