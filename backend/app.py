from flask import Flask, request, jsonify
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
except Exception:
    load_dotenv = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
except Exception:
    ChatGoogleGenerativeAI = None
    ChatPromptTemplate = None
    StrOutputParser = None

# Optional: Twilio for SMS
try:
    from twilio.rest import Client as TwilioClient
except Exception:
    TwilioClient = None

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
        self.langchain_chat = None
        self.langchain_error = None
        self.gemini_model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self._init_langchain()
        # Backward compatible: if you still have GEMINI_ONLY set, reuse it.
        self.llm_only = (
            os.environ.get("LLM_ONLY") or os.environ.get("GEMINI_ONLY") or "true"
        ).strip().lower() == "true"

        # Retry/backoff knobs for rate-limit/quota issues (best-effort).
        self.llm_max_retries = int(os.environ.get("LLM_MAX_RETRIES", "2"))
        self.llm_retry_base_delay_s = float(os.environ.get("LLM_RETRY_BASE_DELAY_S", "1.0"))
        self.llm_retry_max_delay_s = float(os.environ.get("LLM_RETRY_MAX_DELAY_S", "20.0"))
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
        ]

    def _init_langchain(self):
        # Use GEMINI_API_KEY
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            self.langchain_error = "GEMINI_API_KEY not set"
            return
        if not ChatGoogleGenerativeAI:
            self.langchain_error = "LangChain Google GenAI dependencies not installed"
            return
        try:
            self.langchain_chat = ChatGoogleGenerativeAI(
                model=self.gemini_model_name,
                temperature=0.6,
                google_api_key=api_key,
                max_retries=1, # Prevent 60-second backoff hangs on rate limits
                timeout=10.0,  # Prevent infinite hangs
            )
        except Exception as e:
            self.langchain_chat = None
            self.langchain_error = str(e)

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

    def _predict_with_ml(self, message, session_id="default"):
        if not self.ml_model:
            return None

        raw_pred = self.ml_model.predict([message])[0]
        if self.label_encoder is not None:
            try:
                emotion = self.label_encoder.inverse_transform([raw_pred])[0]
            except Exception:
                emotion = str(raw_pred)
        else:
            emotion = str(raw_pred)

        confidence = None
        try:
            if hasattr(self.ml_model, "predict_proba"):
                probabilities = self.ml_model.predict_proba([message])[0]
                confidence = float(max(probabilities))
        except Exception:
            confidence = None

        emotion_text = str(emotion)
        normalized_emotion = emotion_text.strip().lower()
        compact = " ".join(message.lower().split())

        # Guardrail: avoid clearly contradictory labels (e.g., "I feel happy" -> Depression).
        has_positive_signal = any(k in compact for k in self.positive_text_keywords)
        has_negative_signal = any(k in compact for k in self.negative_text_keywords)
        if has_positive_signal and normalized_emotion in self.negative_labels and not has_negative_signal:
            emotion_text = "Happiness"
            normalized_emotion = "happiness"

        response_text = self._build_response_text(message, normalized_emotion, emotion_text, session_id)
        return {
            "emotion": emotion_text,
            "emoji": "🧠",
            "response": response_text,
            "model": "ml",
            "confidence": confidence
        }

    def _build_response_text(self, message, normalized_emotion, emotion_text, session_id="default"):
        compact = " ".join(message.lower().split())
        recent_context = self._get_recent_context(session_id).lower()

        if any(k in compact for k in self.advice_keywords):
            return self._pick_non_repeating("study_advice", self.study_advice_followups)

        if any(k in compact for k in self.study_keywords):
            return self._pick_non_repeating("study_advice", self.study_advice_followups)

        if "study" in recent_context and any(k in compact for k in self.talk_request_keywords):
            return self._pick_non_repeating("study_advice", self.study_advice_followups)

        if any(k in compact for k in self.talk_request_keywords):
            return self._pick_non_repeating("normal_followup", self.normal_followups)

        if compact in self.greeting_keywords:
            return "Hey! I am glad you reached out. How has your day been so far?"

        if normalized_emotion in self.generic_labels:
            return self._pick_non_repeating("normal_followup", self.normal_followups)

        return f"I hear you. It sounds like {emotion_text.lower()}. Want to share a little more so I can support you better?"

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

    def get_response(self, message, session_id="default"):
        """
        Uses an ensemble or priority-based selection to get the most accurate response.
        Priority: LLM -> ML -> Heuristic
        """
        raw_message = message.strip()
        message = raw_message.lower().strip()
        self._store_turn(session_id, "user", raw_message)

        safety_result = self._safety_override(raw_message)
        if safety_result:
            self._store_turn(session_id, "assistant", safety_result.get("response", ""))
            return safety_result
        
        # 1. Try to get a high-quality response from LLM if available
        if self.llm_model:
            try:
                # Add real LLM generation logic here
                pass
            except Exception as e:
                print(f"LLM Model error: {e}")

        # 2. ML-based emotion detection
        if self.ml_model:
            try:
                ml_result = self._predict_with_ml(message, session_id)
                if ml_result:
                    llm_text = self._generate_langchain_response(raw_message, ml_result.get("emotion", "Neutral"), session_id)
                    if llm_text:
                        ml_result["response"] = llm_text
                        ml_result["model"] = "ml+langchain"
                    elif self.llm_only:
                        error_hint = self.langchain_error or "unknown runtime error"
                        ml_result["response"] = f"Gemini is not available right now ({error_hint}). Please verify key, quota, and API access."
                        ml_result["model"] = "gemini_unavailable"
                    self._store_turn(session_id, "assistant", ml_result.get("response", ""))
                    return ml_result
            except Exception as e:
                print(f"ML Model error: {e}")

        # 3. Fallback: Heuristic emotion detection if ML unavailable.
        result = self.heuristic_model.analyze(message)
        result["model"] = "heuristic"
        llm_text = self._generate_langchain_response(raw_message, result.get("emotion", "Neutral"), session_id)
        if llm_text:
            result["response"] = llm_text
            result["model"] = "heuristic+langchain"
        elif self.llm_only:
            error_hint = self.langchain_error or "unknown runtime error"
            result["response"] = f"Gemini is not available right now ({error_hint}). Please verify key, quota, and API access."
            result["model"] = "gemini_unavailable"
        self._store_turn(session_id, "assistant", result.get("response", ""))
        return result

class HeuristicModel:
    def __init__(self):
        self.emotion_patterns = [
            {"keywords": ["stressed", "overwhelmed", "pressure", "burnout"], "emotion": "Stress", "emoji": "😟", 
             "responses": ["I can hear that you're feeling stressed. Take a deep breath with me: in for 4, out for 6.", "You're dealing with a lot. What's one small thing you can control right now?"]},
            {"keywords": ["anxious", "worried", "panic", "fear"], "emotion": "Anxiety", "emoji": "😰", 
             "responses": ["Anxiety can be really overwhelming. Let's ground ourselves: name 5 things you see.", "I'm here for you. Your feelings are valid — try placing a hand on your heart."]},
            {"keywords": ["sad", "depressed", "down", "unhappy", "hopeless", "upset", "heartbroken", "breakup", "break up", "broke up", "alone", "lonely", "no friends", "dont have friends", "don't have friends"], "emotion": "Sadness", "emoji": "😢", 
             "responses": ["I'm sorry you're feeling this way. Would you like to talk about what's on your mind?", "Feeling down is tough, but you aren't alone. I'm here to listen."]},
            {"keywords": ["happy", "good", "great", "wonderful", "joy"], "emotion": "Happiness", "emoji": "😊", 
             "responses": ["That's wonderful! Tell me more about what's making you feel this way.", "I'm so glad to hear that! Celebrating the wins matters."]},
            {"keywords": ["angry", "mad", "frustrated", "furious"], "emotion": "Anger", "emoji": "😠", 
             "responses": ["It sounds like something is really bothering you. Anger is a natural signal. What triggered this?", "I hear your frustration. Want to talk through what's frustrating you?"]},
            {"keywords": ["tired", "sleepy", "fatigue", "no energy"], "emotion": "Fatigue", "emoji": "😴", 
             "responses": ["Rest is so important for your mental health. Have you been able to rest today?", "Your body might be asking you to slow down. Consider a gentle bedtime routine."]},
        ]
        self.default_responses = [
            "Thank you for sharing. How long have you been feeling this way?",
            "I'm here to listen. Tell me more about what's on your mind.",
            "I hear you. What would feel most helpful right now?",
            "I'm listening with no judgment. How's the rest of your day going?",
        ]
        self._last_response_by_emotion = {}

    def analyze(self, message):
        # If user uses contrast words ("but", "however"), the trailing clause
        # usually carries the latest emotional state.
        parts = [message]
        for splitter in [" but ", " however ", " though "]:
            if splitter in message:
                parts = [p.strip() for p in message.split(splitter) if p.strip()]
        search_texts = list(reversed(parts))

        for text in search_texts:
            for pattern in self.emotion_patterns:
                if any(kw in text for kw in pattern["keywords"]):
                    return {
                        "emotion": pattern["emotion"],
                        "emoji": pattern["emoji"],
                        "response": self._pick_non_repeating_response(pattern["emotion"], pattern["responses"])
                    }

        for pattern in self.emotion_patterns:
            if any(kw in message for kw in pattern["keywords"]):
                return {
                    "emotion": pattern["emotion"],
                    "emoji": pattern["emoji"],
                    "response": self._pick_non_repeating_response(pattern["emotion"], pattern["responses"])
                }
        return {
            "emotion": "Neutral",
            "emoji": "🤔",
            "response": self._pick_non_repeating_response("Neutral", self.default_responses)
        }

    def _pick_non_repeating_response(self, emotion, choices):
        if not choices:
            return ""
        last = self._last_response_by_emotion.get(emotion)
        candidates = [c for c in choices if c != last]
        picked = random.choice(candidates or choices)
        self._last_response_by_emotion[emotion] = picked
        return picked

model_manager = ModelManager()

# --- Simple OTP store (in-memory). For production, use a persistent store like Redis or DB.
OTP_STORE = {}  # phone -> {otp, expires}

# Twilio and Supabase config from environment
TWILIO_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_FROM = os.environ.get('TWILIO_FROM_NUMBER')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_ROLE = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')

twilio_client = None
if TwilioClient and TWILIO_SID and TWILIO_TOKEN:
    twilio_client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)

# --- API Routes ---

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "status": "ok",
        "service": "mindful-companion-backend",
        "message": "Backend is running. Use /chat, /chat_stream, /models, /auth/send-otp, /auth/verify-otp"
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
    result = model_manager.get_response(data['message'], session_id=session_id)
    return jsonify(result)

@app.route('/chat_stream', methods=['POST'])
def chat_stream():
    from flask import Response
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
        return response

    # 3. Detect emotion using ML or Heuristics
    ml_result = None
    if model_manager.ml_model:
        ml_result = model_manager._predict_with_ml(message, session_id)
    if not ml_result:
        ml_result = model_manager.heuristic_model.analyze(message)

    emotion_text = ml_result.get("emotion", "Neutral")
    emoji_text = ml_result.get("emoji", "🤔")

    def generate():
        # Send metadata first
        yield f"data: {json.dumps({'type': 'meta', 'emotion': emotion_text, 'emoji': emoji_text})}\n\n"

        recent_turns = model_manager._get_recent_context(session_id)
        if not model_manager.langchain_chat:
            # Fallback to local heuristic response
            res_text = ml_result.get("response", "I'm here for you.")
            yield f"data: {json.dumps({'type': 'chunk', 'text': res_text})}\n\n"
            yield "data: [DONE]\n\n"
            model_manager._store_turn(session_id, "assistant", res_text)
            return

        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are MindfulChat, a warm and empathetic mental wellness companion. Keep responses supportive, concise (1-3 sentences). Do not diagnose."),
            ("human", "Recent conversation:\n{history}\n\nUser message: {message}\nDetected emotion: {emotion}\nWrite a natural supportive response."),
        ])
        chain = prompt | model_manager.langchain_chat | StrOutputParser()

        full_response = ""
        try:
            import time
            for chunk in chain.stream({"history": recent_turns, "message": raw_message, "emotion": emotion_text}):
                if chunk:
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
                    time.sleep(0.01) # Small pause to flush SSE buffer over WSGI securely
        except Exception as e:
            if not full_response:
                fallback_msg = ml_result.get("response", "I hear you, and I am here to listen.")
                model_manager._store_turn(session_id, "assistant", fallback_msg)
                yield f"data: {json.dumps({'type': 'chunk', 'text': fallback_msg})}\n\n"
            else:
                err_msg = " [Gemini API rate limit reached, switched to offline mode]"
                full_response += err_msg
                model_manager._store_turn(session_id, "assistant", full_response)
                yield f"data: {json.dumps({'type': 'chunk', 'text': err_msg})}\n\n"
            yield "data: [DONE]\n\n"
            return

        model_manager._store_turn(session_id, "assistant", full_response)
        yield "data: [DONE]\n\n"

    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
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

if __name__ == '__main__':
    # You can configure the port here (standard is 5000)
    app.run(debug=True, port=int(os.environ.get('PORT', 5000)))
