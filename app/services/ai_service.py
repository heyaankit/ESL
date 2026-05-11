"""OpenAI service abstraction with stub fallback.

When OPENAI_API_KEY is configured, this service makes real API calls.
Otherwise, it returns deterministic stub responses so the API remains functional
for development and testing. The stub can be swapped for a real implementation
by setting the OPENAI_API_KEY environment variable.
"""
from app.config import settings
from app.logger import logger
from typing import Optional


class AIService:
    """Abstraction layer for AI operations (chat, quiz generation, answer evaluation)."""

    def __init__(self):
        self._client = None

    @property
    def is_available(self) -> bool:
        return settings.openai_configured or settings.openai_base_url is not None

    def _get_client(self):
        """Lazy-init OpenAI client when API key or base_url is available."""
        if self._client is None:
            if settings.openai_configured or settings.openai_base_url:
                try:
                    from openai import OpenAI
                    self._client = OpenAI(
                        api_key=settings.openai_api_key or "dummy-key",
                        base_url=settings.openai_base_url or "https://api.openai.com/v1",
                        timeout=settings.openai_timeout_seconds,
                        max_retries=settings.openai_max_retries,
                    )
                except ImportError:
                    logger.warning("openai package not installed. AI features will use stubs.")
        return self._client

    def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """Send messages to the AI model and return the assistant's response.

        Returns a stub response if OpenAI is not configured.
        """
        client = self._get_client()
        if client is None:
            return self._stub_chat_response(messages)

        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._stub_chat_response(messages)

    def generate_quiz_question(
        self,
        lesson_topic: str,
        mode: str = "multiple_choice",
        difficulty: str = "beginner",
    ) -> dict:
        """Generate a quiz question for a given topic.

        Returns a stub question if OpenAI is not configured.
        """
        client = self._get_client()
        if client is None:
            return self._stub_quiz_question(lesson_topic, mode)

        try:
            prompt = (
                f"Generate a {mode} English learning question about '{lesson_topic}' "
                f"for a {difficulty} level Mongolian speaker learning English. "
                f"Return JSON with: question, options (list), correct_answer, feedback."
            )
            messages = [
                {"role": "system", "content": "You are an English teacher creating quiz questions for Mongolian speakers."},
                {"role": "user", "content": prompt},
            ]
            response = self.chat_completion(messages, temperature=0.8, max_tokens=300)
            # Try to parse as JSON; fall back to stub if parsing fails
            import json
            try:
                result = json.loads(response)
                return {
                    "question": result.get("question", ""),
                    "options": result.get("options", []),
                    "correct_answer": result.get("correct_answer", ""),
                    "feedback": result.get("feedback", ""),
                }
            except json.JSONDecodeError:
                return self._stub_quiz_question(lesson_topic, mode)
        except Exception as e:
            logger.error(f"Quiz generation error: {e}")
            return self._stub_quiz_question(lesson_topic, mode)

    def evaluate_answer(
        self,
        question: str,
        user_answer: str,
        correct_answer: str,
    ) -> dict:
        """Evaluate a user's answer with AI feedback.

        Returns a simple exact/fuzzy match result if OpenAI is not configured.
        """
        client = self._get_client()
        if client is None:
            return self._stub_evaluate(question, user_answer, correct_answer)

        try:
            prompt = (
                f"Question: {question}\n"
                f"Correct answer: {correct_answer}\n"
                f"User's answer: {user_answer}\n\n"
                f"Is the user's answer correct? Return JSON: "
                f'{{"is_correct": true/false, "feedback": "explanation", "score": 0-100}}'
            )
            messages = [
                {"role": "system", "content": "You are an English teacher evaluating answers."},
                {"role": "user", "content": prompt},
            ]
            response = self.chat_completion(messages, temperature=0.3, max_tokens=200)
            import json
            try:
                result = json.loads(response)
                return {
                    "is_correct": result.get("is_correct", False),
                    "feedback": result.get("feedback", ""),
                    "score": result.get("score", 0),
                }
            except json.JSONDecodeError:
                return self._stub_evaluate(question, user_answer, correct_answer)
        except Exception as e:
            logger.error(f"Answer evaluation error: {e}")
            return self._stub_evaluate(question, user_answer, correct_answer)

    # ─── Stub implementations ───────────────────────────────────────

    def _stub_chat_response(self, messages: list[dict]) -> str:
        """Deterministic stub chat response for development."""
        last_msg = messages[-1].get("content", "") if messages else ""
        return (
            f"[STUB] I'm your English learning assistant! You said: '{last_msg[:50]}...'. "
            f"Configure OPENAI_API_KEY to enable real AI responses."
        )

    def _stub_quiz_question(self, topic: str, mode: str) -> dict:
        """Deterministic stub quiz question for development."""
        return {
            "question": f"[STUB] Which word relates to '{topic}'?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "Option A",
            "feedback": f"[STUB] Configure OPENAI_API_KEY for real quiz generation.",
        }

    def _stub_evaluate(self, question: str, user_answer: str, correct_answer: str) -> dict:
        """Simple fuzzy match stub for answer evaluation."""
        ua = user_answer.strip().lower()
        ca = correct_answer.strip().lower()

        # Exact match
        if ua == ca:
            return {"is_correct": True, "feedback": "Correct!", "score": 100}

        # Check if user answer is contained in correct answer or vice versa
        if ua in ca or ca in ua:
            return {"is_correct": True, "feedback": "Close enough!", "score": 80}

        # Check semicolon-delimited acceptable answers
        acceptable = [a.strip().lower() for a in correct_answer.split(";")]
        if ua in acceptable:
            return {"is_correct": True, "feedback": "Correct!", "score": 100}

        return {
            "is_correct": False,
            "feedback": f"The correct answer is: {correct_answer}",
            "score": 0,
        }


# Singleton instance
ai_service = AIService()
