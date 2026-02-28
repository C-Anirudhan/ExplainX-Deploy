import os
import google.generativeai as genai
from retrieve import retrieve_combined
from pdf_chroma_ingest import ChromaMultimodalDB
from dotenv import load_dotenv
from mongo import sessions_col
from format_answer import clean_llm_text

load_dotenv()
API = os.getenv("API")


# ---------------- PROMPT MODES ---------------- #
def build_prompt(context, question, mode="regulatory", history=""):
    if mode == "narrative":
        return f"""
You are a professional multimedia narrator.

{history}

CONTEXT:
{context}

TASK:
{question}

Rules:
- Chronological storytelling
- Friendly language
- Use emojis
- Subheadings allowed
- Explain visuals and speech
- CRITICAL: If the provided CONTEXT does not contain the answer, say "The uploaded content does not provide this information." Do not guess.
"""

    return f"""
You are a corporate regulatory analyst.

{history}

CONTEXT:
{context}

TASK:
{question}

Rules:
- No emojis
- No emotional language
- Preserve numbers exactly
- Preserve corporate/legal wording
- Use bullet points only
- Do not add any interpretation
- CRITICAL: If the provided CONTEXT does not contain the answer, reply ONLY with: "The uploaded documents/video do not contain the mathematical or technical information to answer this question." Do not use background metadata to answer.
"""


def get_history(session_id, limit=20):
    """
    Retrieves the last user-bot conversation turns.
    """
    session = sessions_col.find_one({"_id": session_id})

    if not session or "messages" not in session:
        return []

    all_messages = session.get("messages", [])

    conversation = [
        msg for msg in all_messages
        if isinstance(msg, dict) and msg.get("role") in ["user", "assistant"]
    ]

    return conversation[-limit:]


def format_history_for_prompt(session_id):
    """Formats the history array into a readable string for the LLM."""
    if not session_id:
        return ""

    history_data = get_history(session_id)
    if not history_data:
        return ""

    formatted = "--- PREVIOUS CHAT HISTORY ---\n"
    for msg in history_data:
        role = msg.get("role", "Unknown").upper()
        text = msg.get("text", "") or msg.get("content", "")
        formatted += f"{role}: {text}\n"
    formatted += "--- END OF HISTORY ---\n"
    return formatted


# ---------------- LLM CORE ---------------- #
class LLM:
    def __init__(self):
        genai.configure(api_key=API)
        self.MODEL_NAME = "models/gemini-2.5-flash"

    # ---------------- Helpers ---------------- #
    def generate_chat_title(self, question):
        """Generates a smart, 3-4 word title for the chat sidebar."""
        prompt = (
            "Generate a short, catchy title (maximum 4 words) summarizing this question. "
            "Return ONLY the title, no quotes, no extra text, no markdown: "
            f"{question}"
        )
        try:
            raw = genai.GenerativeModel(self.MODEL_NAME).generate_content(prompt).text
            return raw.strip().replace('"', "")
        except Exception:
            return question[:30] + "..."

    def _quick_answer(self, context, question):
        prompt = f"""
Use the context below to answer briefly.

CONTEXT:
{context}

QUESTION: {question}
"""
        return genai.GenerativeModel(self.MODEL_NAME).generate_content(prompt).text.strip()

    def _final_answer(self, context, question, history=""):
        prompt = f"""
Use the context below to answer accurately.

{history}

CONTEXT:
{context}

QUESTION: {question}
"""
        return genai.GenerativeModel(self.MODEL_NAME).generate_content(prompt).text.strip()

    # ---------------- VIDEO ---------------- #
    def summarize_video(self, video_id):
        _, transcripts, frames = retrieve_combined(video_id, "summarize the video fully", 500, 500)
        context = "\n".join([t["document"] for t in transcripts] + [f["document"] for f in frames])
        raw = genai.GenerativeModel(self.MODEL_NAME).generate_content(
            build_prompt(context, "Summarize the full video", mode="narrative")
        ).text
        return clean_llm_text(raw)

    def ask_question(self, video_id, question, session_id=None):
        _, transcripts, frames = retrieve_combined(video_id, question, 30, 30)
        context = "\n".join([t["document"] for t in transcripts] + [f["document"] for f in frames])

        history_str = format_history_for_prompt(session_id)

        raw = genai.GenerativeModel(self.MODEL_NAME).generate_content(
            build_prompt(context, question, mode="regulatory", history=history_str)
        ).text
        return clean_llm_text(raw)

    # ---------------- PDF ---------------- #
    def summarize_pdf(self, chat_id):
        db = ChromaMultimodalDB(chat_id)
        chunks = db.query_text("Summarize all pages", top_k=20)
        raw = genai.GenerativeModel(self.MODEL_NAME).generate_content(
            build_prompt("\n".join(chunks), "Summarize the PDF", mode="regulatory")
        ).text
        return clean_llm_text(raw)

    # ---------------- MULTI-DOC SMART QA ---------------- #
    def ask_question_ppt_pdf(self, chat_id, question):
        session = sessions_col.find_one({"_id": chat_id})
        active_doc = session.get("active_doc") if session else None

        db = ChromaMultimodalDB(chat_id)
        grouped = db.query_grouped(question, only_doc=active_doc)

        if not grouped:
            return "No relevant information found in the uploaded documents."

        history_str = format_history_for_prompt(chat_id)

        if len(grouped) == 1:
            fname, chunks = list(grouped.items())[0]
            sessions_col.update_one({"_id": chat_id}, {"$set": {"active_doc": fname}})
            return clean_llm_text(self._final_answer("\n".join(chunks), question, history=history_str))

        msg = "Your question matches multiple documents:\n\n"
        for fname, chunks in grouped.items():
            short = self._quick_answer("\n".join(chunks[:6]), question)
            msg += f"- {fname}: {short}\n"
        msg += "\nPlease reply with the document name you meant."
        return clean_llm_text(msg)

    def ask_question_multimodal(self, session_id, question):
        """
        Retrieves context from BOTH video (session-scoped) and document DB, then fuses them.
        """
        print(f"--- Multimodal Query: {question} ---")

        # 1. Video context (indexed with video_id=session_id)
        video_context = ""
        try:
            _, transcripts, frames = retrieve_combined(session_id, question, 20, 20)
            video_context = "\n".join(
                [t["document"] for t in transcripts] + [f["document"] for f in frames]
            )
        except Exception as e:
            print(f"Error fetching video context: {e}")
            video_context = "No video context available due to error."

        # 2. PDF/PPT context
        pdf_context = ""
        try:
            pdf_db = ChromaMultimodalDB(session_id)
            pdf_results = pdf_db.query_text(question, top_k=10)
            pdf_context = "\n".join(pdf_results) if isinstance(pdf_results, list) else str(pdf_results)
        except Exception as e:
            print(f"Error fetching PDF context: {e}")
            pdf_context = "No document context available due to error."

        history_str = format_history_for_prompt(session_id)

        system_prompt = f"""
You are a highly intelligent researcher assistant capable of synthesizing information from multiple sources.

You have two distinct sources of information:
1. A VIDEO TRANSCRIPT (visual/auditory content).
2. A DOCUMENT (PDF/PPT slides or text).

Your goal is to answer the user's question by COLLABORATING information from both sources.

{history_str}

--- VIDEO CONTEXT ---
{video_context}

--- DOCUMENT CONTEXT ---
{pdf_context}

--- INSTRUCTIONS ---
- If the answer is found in both, mention how they support each other.
- If the answer is only in one, specify which source it came from.
- If the video explains X and the document explains Y, synthesize them.
- Do not hallucinate. If the answer is not in either context, say so.
"""

        try:
            full_prompt = f"{system_prompt}\n\nUSER QUESTION: {question}"
            raw_response = genai.GenerativeModel(self.MODEL_NAME).generate_content(full_prompt).text
            return clean_llm_text(raw_response)
        except Exception as e:
            print(f"LLM Generation Error: {e}")
            return "I was unable to generate a response due to an internal error."
