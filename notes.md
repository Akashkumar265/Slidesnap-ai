# Prompt design

The V1 prompt is embedded in `services/ai.py`.

For production, split prompts by subject/exam:
- SSC JE Civil
- GATE Civil
- Class 10 Science
- JEE
- NEET

Then add an exam-specific rubric and structured JSON output.
