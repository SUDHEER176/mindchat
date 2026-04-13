from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import random
import os
import time
import re
from datetime import datetime, timedelta
import requests
import joblib
from collections import defaultdict, deque

try:
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
except Exception:
    load_dotenv = None

try:
    IMPORT_ERROR = None
except Exception as e:
    print(f"[Import] Critical Error: {e}")
    IMPORT_ERROR = str(e)

# Optional: Twilio for SMS
try:
    from twilio.rest import Client as TwilioClient
except Exception:
    TwilioClient = None

# DeepFace for Facial Emotion Recognition
try:
    import base64
    import numpy as np
    import cv2
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
    print("[FaceAI] DeepFace loaded successfully.")
except Exception as e:
    DEEPFACE_AVAILABLE = False
    print(f"[FaceAI] DeepFace not available: {e}")

app = Flask(__name__)
CORS(app)

if load_dotenv:
    # Load from this backend folder regardless of the current working directory.
    # override=True makes sure updates to backend/.env take effect after reloads.
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

# --- Configuration & Model Loader ---
# Define your 3 models here. 
# Once you have the files (e.g., .pkl, .pt, or API keys), you can replace these placeholders with real loading logic.

class ModelManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        # Model 1: Current Heuristic/Rule-based Model
        self.heuristic_model = HeuristicModel()
        
        # Model 2: Trained ML classifier + optional label encoder.
        self.ml_model = None
        self.label_encoder = None
        self.ml_model_error = None
        self._load_ml_artifacts()
        
        # Model 3: LLM/Generative Model (e.g., Gemini Flash or Transformers - Placeholder)
        # genai.configure(api_key="YOUR_API_KEY")
        # self.llm_model = genai.GenerativeModel('gemini-1.5-flash')
        self.llm_model = None
        self.generic_labels = {"normal", "neutral", "okay", "ok"}
        self.negative_labels = {"depression", "sadness", "anxiety", "stress", "anger"}
        self.positive_labels = {"happiness", "joy", "happy"}
        self.positive_text_keywords = [
            "happy", "feeling happy", "i feel happy", "good", "great", "joy", "wonderful", "amazing"
        ]
        self.negative_text_keywords = [
            "depressed", "depression", "sad", "hopeless", "upset", "lonely", "breakup", "anxious", "stress"
        ]
        self.keyword_emotion_map = [
            # Sadness/Depression
            (["so sad", "feeling sad", "feel sad", "i am sad", "i'm sad", "im sad", "very sad", "depressed", "depression", "feel down", "feeling down", "feel empty", "feel hopeless", "cant stop crying", "feel like crying", "not good", "not well", "feeling bad", "feel bad", "bad day", "worst day", "breakup", "break up", "broken heart", "heartbroken", "split up", "relationship ended", "dumped", "lonely"], "Sadness"),
            # Anxiety
            (["anxious", "anxiety", "feel anxious", "i feel anxious", "so anxious", "panic", "panicking", "panicked", "nervous", "worried", "worrying", "fear", "scared", "stressed out", "freaking out", "on edge", "cant breathe"], "Anxiety"),
            # Stress
            (["stressed", "so stressed", "overwhelmed", "too much pressure", "under pressure", "burned out", "burnout", "exhausted from", "cant take it", "too much work"], "Stress"),
            # Anger
            (["so angry", "feel angry", "rage", "furious", "pissed off", "hate everything", "hate everyone", "really angry", "frustrated"], "Anger"),
            # Happiness
            (["feel happy", "feeling happy", "so happy", "great day", "amazing day", "wonderful", "blessed", "joy", "excited", "good day", "glad", "awesome"], "Happiness"),
            # Grief / Relationship
            (["breakup", "break up", "split up", "relationship ended", "divorce", "lost him", "lost her", "broken heart"], "Grief"),
        ]
        self.emotion_emoji_map = {
            "Anxiety": "😰",
            "Sadness": "😢",
            "Happiness": "🌟",
            "Stress": "😫",
            "Anger": "😠",
            "Grief": "💔",
            "Neutral": "😐"
        }
        self.normal_followups = [
            "I'm here with you. Want to tell me what happened today?",
            "Of course. We can talk as long as you need. What's on your mind right now?",
            "I'm listening, friend. Start anywhere - I'm not judging.",
            "Thanks for sharing. Do you want to vent, or do you want practical advice?",
            "We can chat. What's feeling heaviest for you at the moment?",
        ]
        self.talk_request_keywords = [
            "talk", "chat", "speak", "listen", "with me", "some time", "need someone"
        ]
        self.study_keywords = [
            "study", "studies", "exam", "exams", "college", "class", "homework", "syllabus", "not studying"
        ]
        self.advice_keywords = [
            "practical advice", "advice", "what should i do", "help me plan", "how to improve"
        ]
        self.study_advice_followups = [
            "Got you. For studies, try this: 25 minutes focused study + 5 minutes break, for 3 rounds. Which subject feels hardest right now?",
            "Let's make it simple: pick one tiny task for the next 20 minutes (like 2 pages or 10 problems). Want help choosing it?",
            "You're not alone in this. Try a 3-step reset now: drink water, clear desk, set a 15-minute timer, and start with the easiest topic.",
            "If focus is low, start with revision instead of new topics for 20 minutes. Small wins first - what topic can you begin with today?",
        ]
        self.greeting_keywords = ["hi", "hello", "hey", "hii", "bro", "broo"]
        self._last_reply_by_bucket = {}
        self.memory_turns = 6
        self.conversation_memory = defaultdict(lambda: deque(maxlen=self.memory_turns))
        self.openai_chat = None
        self.github_chat = None
        self._init_openai()
        self._init_github_models()
        self._init_huggingface()

    def _init_openai(self):
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            try:
                print("[OpenAI] Initializing GPT-4o...")
                self.openai_chat = ChatOpenAI(
                    model="gpt-4o",
                    api_key=openai_key,
                    temperature=0.7,
                    timeout=5
                )
                print("[OpenAI] Initialized successfully.")
            except:
                self.openai_chat = None

    def _init_github_models(self):
        # GitHub PAT used as an API key for GitHub Models
        github_token = os.environ.get("GITHUB_PAT")
        if github_token:
            try:
                print("[GitHub Models] Initializing GPT-4o...")
                self.github_chat = ChatOpenAI(
                    base_url="https://models.inference.ai.azure.com",
                    api_key=github_token,
                    model="gpt-4o",
                    temperature=0.7,
                    timeout=5
                )
                print("[GitHub Models] Initialized successfully.")
            except Exception as e:
                print(f"[GitHub Models] Init failed: {e}")
                self.github_chat = None

    def _init_huggingface(self):
        hf_key = os.environ.get("HUGGINGFACE_API_KEY")
        hf_model = os.environ.get("HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
        if hf_key:
             # Direct API mode - no LangChain init needed for this
             print(f"[HuggingFace] Ready using model: {hf_model}")
             self.hf_ready = True
        else:
             self.hf_ready = False
        self.crisis_keywords = [
            "i want to die",
            "want to die",
            "kill myself",
            "end my life",
            "suicide",
            "suicidal",
            "harm myself",
            "self harm",
            "self-harm",
            "don't want to live",
            "dont want to live",
            "hit someone",
            "hit some one",
            "fight someone",
            "punch someone",
            "hurt someone"
        ]

    def _load_ml_artifacts(self):
        model_path = os.path.join(self.base_dir, "mental_health_model (1).pkl")
        label_encoder_path = os.path.join(self.base_dir, "label_encoder.pkl")

        try:
            if os.path.exists(model_path):
                self.ml_model = joblib.load(model_path)
            else:
                self.ml_model_error = f"Model not found: {model_path}"

            if os.path.exists(label_encoder_path):
                self.label_encoder = joblib.load(label_encoder_path)
        except Exception as e:
            self.ml_model = None
            self.label_encoder = None
            self.ml_model_error = str(e)

    def _keyword_emotion_override(self, message):
        """Fast, reliable keyword-based emotion detection that overrides the ML model."""
        compact = " ".join(message.lower().split())
        for keywords, emotion in self.keyword_emotion_map:
            if any(k in compact for k in keywords):
                return emotion
        return None

    def _predict_with_ml(self, message, session_id="default"):
        # Step 1: Try fast keyword override FIRST — it's more reliable than ML for clear cases
        keyword_emotion = self._keyword_emotion_override(message)

        if self.ml_model:
            try:
                raw_pred = self.ml_model.predict([message])[0]
                if self.label_encoder is not None:
                    try:
                        ml_emotion = self.label_encoder.inverse_transform([raw_pred])[0]
                    except Exception:
                        ml_emotion = str(raw_pred)
                else:
                    ml_emotion = str(raw_pred)
            except Exception as e:
                print(f"ML predict error: {e}")
                ml_emotion = "Normal"
        else:
            ml_emotion = "Normal"
            return None  # No ML model — let heuristic handle it fully

        # Step 2: Use keyword override when ML says Normal but keywords say otherwise
        normalized_ml = ml_emotion.strip().lower()
        if keyword_emotion and normalized_ml in self.generic_labels:
            emotion_text = keyword_emotion
            normalized_emotion = keyword_emotion.lower()
        else:
            emotion_text = str(ml_emotion)
            normalized_emotion = normalized_ml

        confidence = None
        try:
            if hasattr(self.ml_model, "predict_proba"):
                probabilities = self.ml_model.predict_proba([message])[0]
                confidence = float(max(probabilities))
        except Exception:
            confidence = None

        compact = " ".join(message.lower().split())

        # Guardrail: Name introductions should not be classified as mental health issues
        is_name_intro = any(prefix in compact for prefix in ["my name", "i am ", "i'm ", "name is ", "call me "]) or len(message.split()) <= 2
        emotion_keywords = ["sad", "happy", "anxious", "stress", "depress", "angry", "kill", "die"]
        has_emotion_word = any(k in compact for k in emotion_keywords)

        if is_name_intro and not has_emotion_word and normalized_emotion in self.negative_labels:
            emotion_text = "Neutral"
            normalized_emotion = "neutral"

        has_positive_signal = any(k in compact for k in self.positive_text_keywords)
        has_negative_signal = any(k in compact for k in self.negative_text_keywords)
        if has_positive_signal and normalized_emotion in self.negative_labels and not has_negative_signal:
            emotion_text = "Happiness"
            normalized_emotion = "happiness"

        # --- SMART EDUCATIONAL OVERRIDE ---
        edu_resp = self._get_educational_response(message)
        if edu_resp:
            return {
                "emotion": "Neutral",
                "emoji": "📚",
                "response": edu_resp,
                "model": "offline-edu",
                "confidence": 1.0
            }

        response_text = self._build_response_text(message, normalized_emotion, emotion_text, session_id)
        return {
            "emotion": emotion_text,
            "emoji": "🧠",
            "response": response_text,
            "model": "ml",
            "confidence": confidence
        }

    def _get_educational_response(self, message):
        """Provides expert-style static responses for common questions without an LLM."""
        msg = message.lower()
        if "difference" in msg or "vs" in msg or "between" in msg:
            if "sadness" in msg and "depression" in msg:
                return "Great question. Sadness is usually a temporary reaction to a specific event (like a bad day), while depression is a persistent low mood that lasts for weeks and affects your ability to function daily. Would you like to check your symptoms?"
            if "anxiety" in msg and "stress" in msg:
                return "Stress is usually a response to an external pressure (like a deadline), whereas anxiety is an internal reaction that persists even after the stressor is gone. Do you feel like you're experiencing one of these right now?"
        
        if "what is" in msg or "define" in msg:
            if "depression" in msg: return "Depression is more than just feeling blue; it's a medical condition that affects how you feel, think, and handle daily activities. It’s very treatable, though!"
            if "anxiety" in msg: return "Anxiety is your body's natural response to stress. It’s a feeling of fear or apprehension about what’s to come. If it becomes overwhelming, it helps to talk about it."
        
        return None

    def _build_response_text(self, message, normalized_emotion, emotion_text, session_id="default"):
        # Use the JSON-powered heuristic model for dataset-backed responses
        analysis = self.heuristic_model.analyze(message)
        heuristic_response = analysis.get("response", "") if analysis else ""
        
        # Weak/default or overly upbeat responses that shouldn't pair with negative emotions
        weak_responses = ["here to listen", "i'm listening", "please go on", "not sure i understand", "absolutely", "and then?", "tell me more"]
        is_weak = any(weak in heuristic_response.lower() for weak in weak_responses)
        
        # If it's a negative emotion, we don't want upbeat responses from the heuristic
        is_mismatch = normalized_emotion in self.negative_labels and any(upbeat in heuristic_response.lower() for upbeat in ["absolutely", "great", "wonderful", "perfect"])
        
        if heuristic_response and not is_weak and not is_mismatch:
            return heuristic_response

        # Fallback: use emotion-specific replies
        if normalized_emotion == "grief":
             return "I'm so sorry you're going through a loss right now. Relationship endings or losses are incredibly painful. I'm here to listen to whatever you're feeling."
        
        if normalized_emotion == "sadness":
             return "I'm so sorry to hear you're going through a tough time with this. It's completely okay to feel sad or overwhelmed right now. Do you want to share more about what happened?"
        
        if normalized_emotion in self.negative_labels:
            label = emotion_text.lower()
            return f"I hear you. It sounds like you're dealing with {label} right now and it's completely understandable to feel this way. Would you like to talk more about it?"

        compact = " ".join(message.lower().split())
        
        # Humanize the final text before returning
        humanized = self._humanize_response(heuristic_response, normalized_emotion)
        return humanized

    def _humanize_response(self, text, emotion):
        """Converts short/robotic dataset responses into warm, human-sounding ones."""
        t = text.strip()
        
        # 1. If the response is extremely short or generic, provide a high-quality replacement
        generic_trash = ["and?", "and", "anything else?", "continue", "go on", "i see", "ok", "okay"]
        if t.lower() in generic_trash or len(t.split()) < 3:
            if emotion == "sadness":
                return "I'm really listening. Please, tell me more about what's making you feel this way—I'm here to support you."
            if emotion == "anxiety":
                return "It's okay to take your time. What specifically is making you feel anxious or worried right now?"
            if emotion == "stress":
                return "That sounds like a lot to carry. Want to talk about what's adding to your stress today?"
            return "I'm here with you. Please, tell me more about what's on your mind."

        # 2. If it's a negative emotion but the response is too cold, add a warm intro
        if emotion in self.negative_labels and not any(warm in t.lower() for warm in ["sorry", "understand", "hear you", "difficult"]):
             prefixes = ["I hear you, and I'm sorry you're going through this. ", "That sounds really tough. ", "I can tell this is weighing on you. "]
             return random.choice(prefixes) + t

        return t

    def _pick_non_repeating(self, bucket, choices):
        if not choices:
            return ""
        last = self._last_reply_by_bucket.get(bucket)
        candidates = [c for c in choices if c != last]
        picked = random.choice(candidates or choices)
        self._last_reply_by_bucket[bucket] = picked
        return picked

    def _looks_like_rate_limit(self, err: Exception) -> bool:
        text = (str(err) or "").lower()
        return any(
            s in text
            for s in [
                "resource_exhausted",
                "quota exceeded",
                "rate limit",
                "429",
                "too many requests",
                "throttl",
            ]
        )

    def _extract_retry_delay_seconds(self, err: Exception):
        """
        Best-effort parsing for retry hints that show up in some providers.
        Examples seen:
        - "Please retry in 26.7907s"
        - "retryDelay': '26s'"
        """
        text = str(err) or ""
        m = re.search(r"please retry in\s+([0-9]+(?:\.[0-9]+)?)\s*s", text, flags=re.IGNORECASE)
        if m:
            try:
                return max(0.0, float(m.group(1)))
            except Exception:
                pass

        m = re.search(r"retrydelay[^0-9]*([0-9]+)\s*s", text, flags=re.IGNORECASE)
        if m:
            try:
                return max(0.0, float(m.group(1)))
            except Exception:
                pass
        return None

    def _sleep_for_backoff(self, attempt_idx: int, err: Exception):
        hinted = self._extract_retry_delay_seconds(err)
        if hinted is not None:
            delay = min(max(hinted, 0.0), self.llm_retry_max_delay_s)
        else:
            # Exponential backoff with small jitter.
            delay = min(
                self.llm_retry_base_delay_s * (2 ** attempt_idx),
                self.llm_retry_max_delay_s,
            )
            delay = delay * (0.85 + random.random() * 0.3)
        time.sleep(delay)

    def _generate_langchain_response(self, message, emotion_text, session_id):
        if not self.langchain_chat or not ChatPromptTemplate or not StrOutputParser:
            return None
        recent_turns = self._get_recent_context(session_id)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are MindfulChat, a warm and empathetic mental wellness companion. Keep responses supportive, concise (1-3 sentences), non-judgmental, and conversational like a caring friend. Do not diagnose. If risk is unclear, encourage seeking trusted support."),
            ("human", "Recent conversation:\n{history}\n\nUser message: {message}\nDetected emotion: {emotion}\nWrite a natural supportive response that feels continuous with the recent chat."),
        ])
        chain = prompt | self.langchain_chat | StrOutputParser()

        last_err = None
        for attempt in range(self.llm_max_retries + 1):
            try:
                text = chain.invoke({"history": recent_turns, "message": message, "emotion": emotion_text})
                if isinstance(text, str) and text.strip():
                    return text.strip()
                return None
            except Exception as e:
                last_err = e
                if self._looks_like_rate_limit(e) and attempt < self.llm_max_retries:
                    self._sleep_for_backoff(attempt, e)
                    continue
                break

        if last_err is not None:
            self.langchain_error = str(last_err)
        return None

    def _get_recent_context(self, session_id):
        history = self.conversation_memory.get(session_id)
        if not history:
            return "(no previous context)"
        return "\n".join([f"{turn['role']}: {turn['text']}" for turn in history])

    def _store_turn(self, session_id, role, text):
        if not session_id:
            return
        self.conversation_memory[session_id].append({"role": role, "text": text})

    def _safety_override(self, message):
        text = " ".join(message.lower().split())
        if any(k in text for k in self.crisis_keywords):
            # Check specifically for aggression against others
            if any(k in text for k in ["hit", "fight", "punch", "hurt some", "kill some"]):
                return {
                    "emotion": "Aggression",
                    "emoji": "⚠️",
                    "response": (
                        "I hear that you're feeling very frustrated or angry right now. "
                        "However, I'm here to support your well-being, and I can't encourage any form of physical conflict. "
                        "Would you like to talk about what's making you feel this way? We can try to find a safer way to express these feelings."
                    ),
                    "model": "safety"
                }
            
            return {
                "emotion": "Crisis",
                "emoji": "🆘",
                "response": (
                    "I'm really glad you told me. You matter, and you deserve immediate support right now. "
                    "If you might act on these thoughts, please call emergency services now (112/911). "
                    "If you can, contact a trusted person nearby and stay with them. "
                    "If you are in the U.S./Canada, call or text 988 for the Suicide & Crisis Lifeline."
                ),
                "model": "safety"
            }
        return None

    def get_response(self, message, session_id="default", detected_emotion=None):
        """
        DATASET-ONLY MODE: All responses come from MentalHealthChatbotDataset.json
        and keyword matching. No external APIs are called.
        Priority: Safety Override -> ML + Keyword Guard -> Heuristic/JSON Dataset
        """
        raw_message = message.strip()
        message = raw_message.lower().strip()
        self._store_turn(session_id, "user", raw_message)

        # 0. If an emotion was detected externally (e.g. via Camera), prioritize it!
        external_ml_result = None
        if detected_emotion:
            print(f"[FaceAI] Using externally detected emotion: {detected_emotion}")
            external_ml_result = {
                "emotion": detected_emotion,
                "emoji": self.emotion_emoji_map.get(detected_emotion, "🧠"),
                "model": "camera-detected"
            }
            # Still build response based on this emotion
            external_ml_result["response"] = self._build_response_text(raw_message, 
                                                                    detected_emotion.lower(), 
                                                                    detected_emotion, 
                                                                    session_id)

        # 1. Safety override always runs first (crisis / aggression)
        safety_result = self._safety_override(raw_message)
        if safety_result:
            self._store_turn(session_id, "assistant", safety_result.get("response", ""))
            return safety_result

        # Return external result ONLY if safety is clear AND we are strictly in offline mode (placeholder check)
        # For now, let's keep it to allow LLMs to use the emotion.
        pass

        # 2. ML classifier (if file loaded) + keyword guardrail
        if self.ml_model:
            try:
                ml_result = self._predict_with_ml(message, session_id)
                if ml_result:
                    print(f"[Dataset-Only] ML detected: {ml_result.get('emotion')}")
                    ml_result["model"] = "dataset"
                    self._store_turn(session_id, "assistant", ml_result.get("response", ""))
                    return ml_result
            except Exception as e:
                print(f"ML predict error: {e}")

        # 3. Try Gemini fallback if match is weak, else use pure heuristic/JSON
        result = self.heuristic_model.analyze(message)
        # 1. Attempt GitHub Models (Primary - New!)
        if self.github_chat:
            try:
                recent_turns = self._get_recent_context(session_id)
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are MindfulChat, an empathetic wellness friend. 1-2 sentences."),
                    ("human", f"Previous context:\n{{history}}\n\nUser: {{message}} (Visual Emotion: {detected_emotion if detected_emotion else 'Not detected'})"),
                ])
                chain = prompt | self.github_chat | StrOutputParser()
                resp = chain.invoke({"history": recent_turns, "message": raw_message})
                if resp:
                    result["response"] = resp.strip()
                    result["model"] = "github-models-gpt4o"
                    self._store_turn(session_id, "assistant", result["response"])
                    return result
            except:
                pass # Fall to OpenAI

        # 2. Attempt OpenAI (Legacy)
        if self.openai_chat:
            try:
                recent_turns = self._get_recent_context(session_id)
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are MindfulChat, a world-class empathetic wellness friend. 1-2 sentences."),
                    ("human", f"Recent History:\n{{history}}\n\nUser: {{message}} (Visual Emotion: {detected_emotion if detected_emotion else 'Not detected'})"),
                ])
                chain = prompt | self.openai_chat | StrOutputParser()
                resp = chain.invoke({"history": recent_turns, "message": raw_message})
                if resp:
                    result["response"] = resp.strip()
                    result["model"] = "openai-gpt4o"
                    self._store_turn(session_id, "assistant", result["response"])
                    return result
            except:
                pass # Fail to HF

        # 2. Attempt Hugging Face (Direct Fallback)
        hf_key = os.environ.get("HUGGINGFACE_API_KEY")
        if hf_key:
            try:
                hf_model = os.environ.get("HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
                prompt = f"Expert Supporter: You are MindfulChat. Focus on empathy. 1-2 sentences.\n\nUser: {raw_message}\nMindfulChat:"
                hf_resp = requests.post(
                    f"https://api-inference.huggingface.co/models/{hf_model}",
                    headers={"Authorization": f"Bearer {hf_key}"},
                    json={"inputs": prompt, "parameters": {"max_new_tokens": 150, "return_full_text": False}},
                    timeout=6
                )
                if hf_resp.status_code == 200:
                    data = hf_resp.json()
                    text = data[0].get("generated_text", "") if isinstance(data, list) else data.get("generated_text", "")
                    if text:
                        clean_text = text.split("MindfulChat:")[-1].strip()
                        result["response"] = clean_text
                        result["model"] = "huggingface-direct"
                        self._store_turn(session_id, "assistant", result["response"])
                        return result
            except:
                pass

        # 3. Dataset Lookup (Instant Fallback)
        if not detected_emotion:
            ml_result = self._predict_with_ml(raw_message, session_id)
            result["emotion"] = ml_result.get("emotion", "Normal")
            result["response"] = self._humanize_response(ml_result.get("response", "I'm here for you."), result["emotion"])
        else:
            result["emotion"] = detected_emotion
            # We already built a response in external_ml_result or can build it here
            res = self._build_response_text(raw_message, detected_emotion.lower(), detected_emotion, session_id)
            result["response"] = self._humanize_response(res, detected_emotion)
        
        result["model"] = "offline-humanized"
        self._store_turn(session_id, "assistant", result["response"])
        return result

class HeuristicModel:
    def __init__(self, dataset_path=None):
        self.intents = []
        self.dataset_path = dataset_path or os.path.join(os.path.dirname(__file__), "MentalHealthChatbotDataset.json")
        self._load_dataset()
        self._last_response_by_tag = {}

    def _load_dataset(self):
        try:
            if os.path.exists(self.dataset_path):
                import json
                with open(self.dataset_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.intents = data.get('intents', [])
                print(f"Loaded {len(self.intents)} intents from dataset.")
            else:
                print(f"Dataset not found at {self.dataset_path}, using empty intents.")
        except Exception as e:
            print(f"Error loading dataset: {e}")

    def analyze(self, message):
        message = message.lower().strip()
        best_tag = None
        max_score = 0
        
        # Simple keyword overlap matching
        words = set(re.findall(r'\w+', message))
        
        for intent in self.intents:
            tag = intent.get('tag')
            patterns = intent.get('patterns', [])
            
            for pattern in patterns:
                p_words = set(re.findall(r'\w+', pattern.lower()))
                if not p_words: continue
                
                # Filter out very common filler words from the match calculation
                filler_words = {"i", "want", "to", "be", "do", "the", "a", "an", "is", "am", "are", "some", "someone", "somebody"}
                significant_words = words - filler_words
                significant_p_words = p_words - filler_words
                
                if not significant_p_words:
                    # Fallback for very short patterns like "Hi"
                    score = len(words.intersection(p_words)) / len(p_words)
                else:
                    score = len(significant_words.intersection(significant_p_words)) / len(significant_p_words)
                
                # Boost for exact substring matches of the full pattern
                if pattern.lower() in message:
                    score += 1.5
                    
                if score > max_score:
                    max_score = score
                    best_tag = tag

        res = {
            "emotion": "Neutral",
            "emoji": "🤔",
            "response": "I'm here to listen. Tell me more about what's on your mind.",
            "max_score": max_score
        }

        if best_tag and max_score > 0.6:
            intent = next((i for i in self.intents if i['tag'] == best_tag), None)
            if intent:
                # Map dataset tags to our internal emotion labels if possible
                emotion_map = {
                    "stressed": "Stress",
                    "sad": "Sadness",
                    "happy": "Happiness",
                    "angry": "Anger",
                    "anxious": "Anxiety",
                    "neutral-response": "Neutral",
                    "greeting": "Neutral",
                    "name": "Neutral"
                }
                res.update({
                    "emotion": emotion_map.get(best_tag, best_tag.capitalize()),
                    "emoji": self._get_emoji(best_tag),
                    "response": self._pick_non_repeating_response(best_tag, intent.get('responses', []))
                })
        return res

    def _get_emoji(self, tag):
        emojis = {
            "stressed": "😟",
            "sad": "😢",
            "happy": "😊",
            "angry": "😠",
            "anxious": "😰",
            "help": "🆘",
            "greeting": "👋",
            "name": "🤝",
            "thanks": "🙏",
            "goodbye": "👋"
        }
        return emojis.get(tag, "🤔")

    def _pick_non_repeating_response(self, tag, choices):
        if not choices:
            return "I'm listening."
        last = self._last_response_by_tag.get(tag)
        candidates = [c for c in choices if c != last]
        picked = random.choice(candidates or choices)
        self._last_response_by_tag[tag] = picked
        return picked

model_manager = ModelManager()

# --- API Routes ---

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "status": "ok",
        "service": "mindful-companion-backend",
        "message": "Backend is running. Use /chat, /chat_stream"
    }), 200


@app.route('/favicon.ico', methods=['GET'])
def favicon():
    return ('', 204)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    session_id = data.get("session_id", "default")
    detected_emotion = data.get("detected_emotion")
    result = model_manager.get_response(data['message'], session_id=session_id, detected_emotion=detected_emotion)
    return jsonify(result)

@app.route('/chat_stream', methods=['POST', 'OPTIONS'])
def chat_stream():
    if request.method == 'OPTIONS':
        # Preflight request
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response, 204

    import json
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    session_id = data.get("session_id", "default")
    raw_message = data['message'].strip()
    message = raw_message.lower()

    # 1. Store user message
    model_manager._store_turn(session_id, "user", raw_message)

    # 2. Check safety
    safety_result = model_manager._safety_override(raw_message)
    if safety_result:
        def safety_gen():
            yield f"data: {json.dumps({'type': 'meta', 'emotion': safety_result['emotion'], 'emoji': safety_result['emoji']})}\n\n"
            yield f"data: {json.dumps({'type': 'chunk', 'text': safety_result['response']})}\n\n"
            yield "data: [DONE]\n\n"
        model_manager._store_turn(session_id, "assistant", safety_result['response'])
        response = Response(safety_gen(), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    # 3. Detect emotion using ML or Heuristics (unless provided)
    detected_emotion = data.get("detected_emotion")
    if detected_emotion:
        emotion_text = detected_emotion
        emoji_text = model_manager.emotion_emoji_map.get(detected_emotion, "🧠")
        ml_result = {"emotion": emotion_text, "emoji": emoji_text}
    else:
        ml_result = model_manager._predict_with_ml(message, session_id)
        if not ml_result:
            ml_result = model_manager.heuristic_model.analyze(message)
        emotion_text = ml_result.get("emotion", "Neutral")
        emoji_text = ml_result.get("emoji", "🤔")

    def generate():
        # Send metadata first
        yield f"data: {json.dumps({'type': 'meta', 'emotion': emotion_text, 'emoji': emoji_text})}\n\n"
        
        # 1. Try GitHub Models Stream
        if model_manager.github_chat:
            try:
                recent_turns = model_manager._get_recent_context(session_id)
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are MindfulChat, an empathetic friend. 1-2 sentences."),
                    ("human", f"History:\n{{history}}\n\nUser: {{message}} (Visual Emotion: {detected_emotion if detected_emotion else 'Not detected'})"),
                ])
                chain = prompt | model_manager.github_chat | StrOutputParser()
                full_resp = ""
                for chunk in chain.stream({"history": recent_turns, "message": raw_message}):
                    if chunk:
                        full_resp += chunk
                        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
                yield "data: [DONE]\n\n"
                model_manager._store_turn(session_id, "assistant", full_resp)
                return
            except:
                pass

        # 2. Try OpenAI Stream
        if model_manager.openai_chat:
            try:
                recent_turns = model_manager._get_recent_context(session_id)
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are MindfulChat, a warm world-class empathetic friend. 1-2 sentences."),
                    ("human", f"History:\n{{history}}\n\nUser: {{message}} (Visual Emotion: {detected_emotion if detected_emotion else 'Not detected'})"),
                ])
                chain = prompt | model_manager.openai_chat | StrOutputParser()
                full_resp = ""
                for chunk in chain.stream({"history": recent_turns, "message": raw_message}):
                    if chunk:
                        full_resp += chunk
                        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
                yield "data: [DONE]\n\n"
                model_manager._store_turn(session_id, "assistant", full_resp)
                return
            except:
                pass

        # Try Hugging Face (Direct Fallback)
        hf_key = os.environ.get("HUGGINGFACE_API_KEY")
        if hf_key:
            try:
                hf_model = os.environ.get("HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
                prompt = f"Expert Supporter: You are MindfulChat. Focus on empathy. 1-2 sentences.\n\nUser: {raw_message}\nMindfulChat:"
                hf_resp = requests.post(
                    f"https://api-inference.huggingface.co/models/{hf_model}",
                    headers={"Authorization": f"Bearer {hf_key}"},
                    json={"inputs": prompt, "parameters": {"max_new_tokens": 150, "return_full_text": False}},
                    timeout=6
                )
                if hf_resp.status_code == 200:
                    data = hf_resp.json()
                    text = data[0].get("generated_text", "") if isinstance(data, list) else data.get("generated_text", "")
                    if text:
                        clean_text = text.split("MindfulChat:")[-1].strip()
                        yield f"data: {json.dumps({'type': 'chunk', 'text': clean_text})}\n\n"
                        yield "data: [DONE]\n\n"
                        model_manager._store_turn(session_id, "assistant", clean_text)
                        return
            except:
                pass

        # Dataset Lookup (Fallback)
        res_text = model_manager._humanize_response(ml_result.get("response", "I'm here for you."), emotion_text)
        for bit in res_text.split(" "):
            yield f"data: {json.dumps({'type': 'chunk', 'text': bit + ' '})}\n\n"
            time.sleep(0.05)
        yield "data: [DONE]\n\n"
        model_manager._store_turn(session_id, "assistant", res_text)

    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/models', methods=['GET'])
def models_status():
    """Check the status/readiness of the 3 models."""
    if model_manager.langchain_chat and model_manager.langchain_error:
        model_3_status = f"LangChain Gemini (Loaded, runtime warning: {model_manager.langchain_error})"
    elif model_manager.langchain_chat:
        model_3_status = "LangChain Gemini (Loaded)"
    else:
        model_3_status = f"LangChain Gemini (Not Loaded: {model_manager.langchain_error or 'not configured'})"

    return jsonify({
        "model_1": "Heuristic (Active)",
        "model_2": "ML Classifier (Loaded)" if model_manager.ml_model else f"ML Classifier (Not Loaded: {model_manager.ml_model_error or 'missing file'})",
        "model_3": model_3_status
    })


# --- Phone signup endpoints ---
def generate_otp():
    return f"{random.randint(0, 999999):06d}"

@app.route('/auth/send-otp', methods=['POST'])
def send_otp():
    data = request.json or {}
    phone = data.get('phone')
    if not phone:
        return jsonify({'error': 'phone is required'}), 400

    otp = generate_otp()
    expires = datetime.utcnow() + timedelta(minutes=5)
    OTP_STORE[phone] = {'otp': otp, 'expires': expires}

    # Send SMS via Twilio if configured
    if twilio_client and TWILIO_FROM:
        try:
            twilio_client.messages.create(
                body=f"Your verification code is: {otp}",
                from_=TWILIO_FROM,
                to=phone
            )
        except Exception as e:
            return jsonify({'error': 'failed to send SMS', 'detail': str(e)}), 500
    else:
        # For local/dev, log and return OTP when SMS provider is not configured.
        print(f"OTP for {phone}: {otp}")
        return jsonify({'status': 'otp_sent', 'expires_in_seconds': 300, 'otp': otp}), 200

    return jsonify({'status': 'otp_sent', 'expires_in_seconds': 300}), 200


@app.route('/auth/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json or {}
    phone = data.get('phone')
    otp = data.get('otp')
    if not phone or not otp:
        return jsonify({'error': 'phone and otp are required'}), 400

    entry = OTP_STORE.get(phone)
    if not entry:
        return jsonify({'error': 'no otp requested for this phone'}), 400

    if datetime.utcnow() > entry['expires']:
        del OTP_STORE[phone]
        return jsonify({'error': 'otp expired'}), 400

    if otp != entry['otp']:
        return jsonify({'error': 'invalid otp'}), 400

    # OTP valid — create user in Supabase via admin endpoint
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE:
        # Cleanup OTP and return success without creating remote user
        del OTP_STORE[phone]
        return jsonify({'status': 'verified', 'note': 'supabase not configured'}), 200

    try:
        url = SUPABASE_URL.rstrip('/') + '/auth/v1/admin/users'
        headers = {
            'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE}',
            'Content-Type': 'application/json'
        }
        payload = {
            'phone': phone
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code not in (200, 201):
            return jsonify({'error': 'failed to create user', 'detail': resp.text}), 500

        user = resp.json()
        del OTP_STORE[phone]
        return jsonify({'status': 'verified', 'user': user}), 200
    except Exception as e:
        return jsonify({'error': 'exception creating user', 'detail': str(e)}), 500

@app.route('/analyze-face', methods=['POST'])
def analyze_face():
    """
    Accepts a base64 image from the frontend camera and returns
    the detected facial emotion using DeepFace.
    """
    if not DEEPFACE_AVAILABLE:
        return jsonify({'error': 'DeepFace not available on this server.'}), 503

    data = request.json or {}
    image_data = data.get('image')  # expects: "data:image/jpeg;base64,..."

    if not image_data:
        return jsonify({'error': 'No image provided'}), 400

    try:
        import traceback
        # Strip the base64 header if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        # Decode and convert to OpenCV image
        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({'error': 'Could not decode image'}), 400

        # Analyze with DeepFace
        # We try RetinaFace first as it's most robust, then OpenCV, then skip
        try:
            print("[FaceAI] Starting analysis with RetinaFace...")
            results = DeepFace.analyze(
                frame,
                actions=['emotion'],
                enforce_detection=False,
                detector_backend='retinaface',
                align=False,
                silent=True
            )
        except Exception as e1:
            print(f"[FaceAI] RetinaFace failed: {e1}. Trying OpenCV...")
            try:
                results = DeepFace.analyze(
                    frame,
                    actions=['emotion'],
                    enforce_detection=False,
                    detector_backend='opencv',
                    align=False,
                    silent=True
                )
            except Exception as e2:
                print(f"[FaceAI] OpenCV failed: {e2}. Final fallback to 'skip'...")
                results = DeepFace.analyze(
                    frame,
                    actions=['emotion'],
                    enforce_detection=False,
                    detector_backend='skip',
                    silent=True
                )

        # Handle both single and list results
        result = results[0] if isinstance(results, list) else results
        dominant_emotion = result.get('dominant_emotion', 'neutral')
        emotion_scores = result.get('emotion', {})

        # Map DeepFace emotions to our internal labels
        # Map DeepFace emotions to our internal labels
        emotion_map = {
            'angry':    {'label': 'Anger',    'emoji': '😠'},
            'disgust':  {'label': 'Anger',    'emoji': '😠'},
            'fear':     {'label': 'Anxiety',  'emoji': '😰'},
            'happy':    {'label': 'Happiness','emoji': '🌟'},
            'sad':      {'label': 'Sadness',  'emoji': '😢'},
            'surprise': {'label': 'Anxiety',  'emoji': '😮'},
            'neutral':  {'label': 'Neutral',  'emoji': '😐'},
        }
        mapped = emotion_map.get(dominant_emotion, {'label': 'Neutral', 'emoji': '😐'})
        
        # Cast to float to avoid "Object of type float32 is not JSON serializable"
        confidence = float(emotion_scores.get(dominant_emotion, 0))
        all_scores = {str(k): float(v) for k, v in emotion_scores.items()}

        return jsonify({
            'emotion': mapped['label'],
            'emoji': mapped['emoji'],
            'raw': str(dominant_emotion),
            'confidence': round(confidence, 1),
            'all_scores': {k: round(v, 1) for k, v in all_scores.items()}
        })

    except Exception as e:
        import traceback
        error_msg = str(e)
        print("\n--- DEEPFACE ERROR ---")
        traceback.print_exc()
        print("----------------------\n")
        # Return a more descriptive error if possible
        return jsonify({
            'error': f'Analysis failed: {error_msg}',
            'suggestion': 'Check if your internet connection is stable (to download models) and if the image is clear.'
        }), 500


if __name__ == '__main__':
    # Force 0.0.0.0 for external visibility (Render/Docker)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
