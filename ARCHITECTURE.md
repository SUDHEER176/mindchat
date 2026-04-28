# 🏗️ Mindful Companion — Architecture Document

> A full technical reference covering every component, data flow, module, and design decision in the Mindful Companion (MindfulChat) codebase.

---

## 📁 1. Project Structure

```
mindful-companion/
├── backend/                          # Flask API & AI Brain
│   ├── app.py                        # Main server: routes, models, AI logic
│   ├── MentalHealthChatbotDataset.json  # Curated intent/response dataset (80 intents)
│   ├── mental_health_model (1).pkl   # Trained Scikit-Learn ML classifier
│   ├── label_encoder.pkl             # Label encoder for ML model output
│   ├── setup_db.sql                  # SQL: creates the profiles table in Supabase
│   ├── signup_confirmation_template.html  # Custom Supabase email confirmation template
│   ├── requirements.txt              # Python dependencies
│   └── .env                         # Secrets: API keys, DB credentials
│
└── frontend/                         # React + Vite app
    ├── src/
    │   ├── pages/
    │   │   ├── Login.tsx             # Auth page (Email + Phone OTP signup/signin)
    │   │   ├── Chat.tsx              # Main chat interface with SSE streaming
    │   │   ├── Journal.tsx           # Private journaling with localStorage
    │   │   ├── MoodTracker.tsx       # Daily mood logging with chart visualization
    │   │   ├── Resources.tsx         # Mental health resource hub
    │   │   └── Index.tsx             # Landing/home page
    │   ├── components/
    │   │   ├── FaceScanner.tsx       # Webcam-based facial emotion detection
    │   │   ├── Navbar.tsx            # Top navigation bar
    │   │   ├── NotificationBell.tsx  # In-app notification UI
    │   │   ├── ThemeToggle.tsx       # Light/Dark mode switcher
    │   │   └── NavLink.tsx           # Reusable nav link component
    │   ├── contexts/
    │   │   └── NotificationsContext.tsx  # Global notification state management
    │   ├── lib/
    │   │   ├── supabase.ts           # Supabase client initialization
    │   │   ├── chatbot.ts            # API client: SSE streaming & emotion patterns
    │   │   └── utils.ts              # Shared utility functions
    │   └── hooks/                    # Custom React hooks (e.g., use-toast)
    └── .env                          # VITE_ prefixed public env vars
```

---

## 2. System Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                  USER's Browser                      │
│                                                      │
│  ┌──────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │ FaceScanner│  │  Chat.tsx    │   │  Login.tsx  │  │
│  │ (Webcam) │   │ (SSE Client) │   │ (Auth Form) │  │
│  └────┬─────┘   └──────┬───────┘   └──────┬──────┘  │
│       │ base64 img      │ POST /chat_stream │ signUp  │
└───────┼────────────────┼──────────────────┼──────────┘
        │                │                  │
        ▼                ▼                  ▼
┌────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Flask Backend │  │  Flask Backend   │  │   Supabase Cloud  │
│  /analyze-face │  │  /chat_stream    │  │   auth.users      │
│  (DeepFace AI) │  │  (Intelligence   │  │   public.profiles │
└────────┬───────┘  │   Orchestrator)  │  └──────────────────┘
         │          └──────┬───────────┘
 Emotion Label             │
 (Happy/Sad/etc.)          │ Priority Chain
         │                 ▼
         │    ┌────────────────────────┐
         │    │ 1. Scope Guardrail     │ ← Blocks coding/tech requests
         │    │ 2. Crisis/Safety Check │ ← Keywords: suicide, self-harm, etc.
         │    │ 3. Scikit-Learn ML     │ ← .pkl classifier (Tier 1)
         │    │ 4. GitHub Models GPT-4o│ ← Cloud LLM via LangChain (Tier 2)
         │    │ 5. Heuristic Dataset   │ ← JSON lookup engine (Tier 3)
         │    └────────────────────────┘
         │                 │
         └─────────────────┘
         Injected as `detected_emotion`
         into the LLM prompt context
```

---

## 3. Backend — `app.py`

### 3.1 Flask Application Setup
- Framework: **Flask** with **Flask-CORS** enabled for all origins.
- Runs on `0.0.0.0:5000` for local and cloud deployment compatibility (Render/Docker).
- All imports are guarded with try/except so the server starts even if optional dependencies (DeepFace, LangChain, Twilio) are unavailable.

### 3.2 ModelManager Class
The central intelligence controller. Instantiated once as `model_manager` at startup.

| Attribute | Description |
|---|---|
| `heuristic_model` | Instance of `HeuristicModel` — dataset-based intent matcher |
| `ml_model` | Scikit-Learn pipeline loaded from `mental_health_model (1).pkl` |
| `label_encoder` | Loaded from `label_encoder.pkl` — decodes numeric class IDs to emotion names |
| `gemini_chat` | LangChain `ChatGoogleGenerativeAI` (Primary LLM, gemini-2.5-flash) |
| `github_chat` | LangChain `ChatOpenAI` pointed at GitHub Models (GPT-4o) |
| `openai_chat` | Direct OpenAI GPT-4o (if key provided) |
| `conversation_memory` | `defaultdict(deque)` — stores last 6 turns per session |
| `crisis_keywords` | Hard-coded list: "suicide", "self-harm", "i want to die", etc. |

### 3.3 AI Response Priority Chain

When a user message arrives, `get_response()` runs through the following sequence in strict order:

1. **Scope Guardrail** (`_non_mental_health_redirect`)
   - Detects tech keywords (python, flask, tensorflow, sql, etc.)
   - Returns a gentle redirect: *"I'm a mental wellness supporter, not a coding tutor."*

2. **Crisis Safety Override** (`_safety_override`)
   - Matches crisis keywords (self-harm, suicide, "want to die").
   - Returns emergency contacts immediately (112/911, 988 Lifeline).
   - For aggression keywords (hit, punch, fight), returns de-escalation response.

3. **ML Classifier** (`_predict_with_ml`)
   - Runs text through the Scikit-Learn pipeline.
   - If ML says "Normal" but keywords say otherwise → keyword override wins.
   - Smart guardrail: name introductions ("my name is X") are not classified as negative.

4. **Keyword Emotion Override** (`_keyword_emotion_override`)
   - Fast, deterministic keyword matching over the raw message.
   - Maps phrases like "so sad", "breakup", "anxious" to emotion labels.

5. **GitHub Models / Gemini LLM** (via LangChain)
   - Builds a prompt with recent conversation history + detected emotion.
   - Streams the response back word-by-word via SSE.

6. **HeuristicModel / JSON Dataset** (final fallback)
   - Word overlap scoring against 80 curated intents.
   - Returns randomized, non-repeating response from the matching intent.
   - Responses are humanized via `_humanize_response()`.

### 3.4 HeuristicModel Class
- Loads `MentalHealthChatbotDataset.json` (80 intents, each with `tag`, `patterns`, `responses`).
- Uses **word overlap scoring** between user message and intent patterns.
- Boosts score by `+1.5` for exact substring pattern matches.
- Filters filler words ("i", "to", "a", "the", etc.) from scoring.
- Picks non-repeating responses per intent tag to prevent robotic loops.

### 3.5 Conversation Memory
```python
self.conversation_memory = defaultdict(lambda: deque(maxlen=6))
```
- Per-session turn history (user + assistant), capped at 6 turns.
- Session ID is a client-generated UUID stored in `localStorage`.
- History is injected into LLM prompts for contextual, coherent responses.

### 3.6 Educational Response Engine (`_get_educational_response`)
- Detects questions starting with "what is", "difference between", "define".
- Returns expert-level static answers for: sadness vs. depression, anxiety vs. stress.
- Avoids unnecessary LLM calls for common informational queries.

---

## 4. Backend API Routes

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Health check — returns service status |
| `GET` | `/favicon.ico` | Returns 204 (no content) |
| `POST` | `/chat` | Non-streaming chat endpoint — returns full JSON response |
| `POST` | `/chat_stream` | **Primary** — SSE streaming chat endpoint |
| `GET` | `/models` | Returns status of all 3 AI model tiers |
| `POST` | `/auth/send-otp` | Generates & sends 6-digit OTP via Twilio SMS |
| `POST` | `/auth/verify-otp` | Validates OTP, creates user in Supabase via admin API |
| `POST` | `/analyze-face` | Accepts base64 image, returns DeepFace emotion analysis |

---

## 5. Server-Sent Events (SSE) Streaming

### How it works
1. Frontend calls `POST /chat_stream` with the message and session ID.
2. Flask returns `Response(generate(), mimetype='text/event-stream')`.
3. The generator yields JSON-encoded events:
   - **Meta event**: `{"type": "meta", "emotion": "Sadness", "emoji": "😢"}`
   - **Chunk events**: `{"type": "chunk", "text": "I hear "}` (word-by-word)
   - **Done event**: `[DONE]`
4. Frontend reads the stream using `ReadableStream` API in `chatbot.ts`.
5. Each chunk appends to the bot message in real time — no loading wait.

### Production headers set on every SSE response
```
Cache-Control: no-cache
X-Accel-Buffering: no
Access-Control-Allow-Origin: *
```

---

## 6. Facial Emotion Recognition (FaceAI)

### Module: `FaceScanner.tsx` (Frontend) + `/analyze-face` (Backend)

**How it works:**
1. `FaceScanner.tsx` accesses the device webcam using `getUserMedia`.
2. Captures a frame as a base64-encoded JPEG and POSTs it to `/analyze-face`.
3. Flask decodes the image using **OpenCV** (`cv2.imdecode`).
4. **DeepFace** runs facial analysis with a 3-tier detector fallback:
   - `RetinaFace` (most accurate)
   - `OpenCV` (fallback)
   - `skip` (final fallback, no face detection required)
5. The dominant emotion is mapped to internal labels:

| DeepFace label | Internal label | Emoji |
|---|---|---|
| angry / disgust | Anger | 😠 |
| fear / surprise | Anxiety | 😰 |
| happy | Happiness | 🌟 |
| sad | Sadness | 😢 |
| neutral | Neutral | 😐 |

6. The emotion result is stored in `Chat.tsx` state (`lastFaceEmotion`).
7. When the user sends their next message, the emotion is injected as `detected_emotion` into the `/chat_stream` POST body — the LLM uses it to adjust its tone.

---

## 7. Authentication — Supabase

### 7.1 How Auth Works
- **Library:** `@supabase/supabase-js` on the frontend.
- **Client:** Created in `src/lib/supabase.ts` using `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
- **Email flow:** `supabase.auth.signUp()` → Supabase sends a confirmation email → user clicks link → confirmed.
- **Phone flow:** `supabase.auth.signInWithOtp({ phone })` → SMS OTP → `supabase.auth.verifyOtp()`.
- **Login:** `supabase.auth.signInWithPassword({ email, password })`.

### 7.2 Rate Limiting (Common Issue)
Supabase free tier enforces strict IP-based rate limits:
- **3 signup emails per hour** per project (default). 
- **429 Too Many Requests** is returned when this limit is exceeded.

**Fixes (in order of preference):**
1. Disable "Confirm email" in Supabase Dashboard → Authentication → Providers → Email.
2. Increase rate limit in Authentication → Rate Limits.
3. Create users manually: Supabase Dashboard → Authentication → Users → Add User.

### 7.3 Profiles Table (Supabase Database)
Defined in `setup_db.sql`. Created alongside `auth.users`.

```sql
CREATE TABLE public.profiles (
  id        UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  full_name TEXT,
  email     TEXT UNIQUE,
  phone     TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

**Row Level Security policies:**
- Users can only `SELECT`, `INSERT`, and `UPDATE` their own row (`auth.uid() = id`).
- A trigger auto-updates `updated_at` on every row update.

**When is it written?** After a successful login/signup in `persistUserAndGoToDashboard()` inside `Login.tsx`, via `supabase.from("profiles").upsert(...)`.

---

## 8. Frontend — Pages

### 8.1 `Login.tsx`
- Supports two auth modes toggled by radio: **Email** and **Phone**.
- Email mode: standard signup/signin with name field on signup.
- Phone mode: sends OTP via Supabase, then verifies with `verifyOtp()`.
- On success, calls `persistUserAndGoToDashboard()` which upserts to `profiles` and navigates to `/chat`.

### 8.2 `Chat.tsx`
- Maintains a `Message[]` array in state.
- Sends messages using `streamAnalyzeAndRespond()` from `chatbot.ts`.
- Displays a **typing indicator** (3-dot bounce animation) while waiting for the first SSE chunk.
- Integrates `FaceScanner` component — captured emotion is shown as a pill badge and sent with the next message.
- Shows **quick prompt buttons** ("I feel stressed", "I feel anxious") on the first load.
- Uses `useNotifications()` to show an in-app warning if the backend is unreachable.

### 8.3 `Journal.tsx`
- Private journaling feature, stored entirely in **`localStorage`** — never sent to any server.
- Three views (animated with Framer Motion): Entry List → Create Entry → Read Entry.
- Optional mood emoji tag (8 options) attached to each entry.
- Entries are timestamped and formatted using the `date-fns` library.

### 8.4 `MoodTracker.tsx`
- Daily mood check-in with 5 levels: Terrible (1) → Great (5).
- Stores entries in **`localStorage`** keyed by `"moodEntries"`.
- Calculates and displays consecutive day **streak**.
- Renders a **14-day Area Chart** using the `recharts` library.
- Fires an in-app notification on every mood log via `useNotifications()`.

### 8.5 `Resources.tsx`
- Static resource hub with curated mental health articles and emergency contacts.
- No backend dependency — fully client-rendered.

### 8.6 `Index.tsx`
- Landing/home page with hero section, feature highlights, and CTA to `/chat` or `/login`.

---

## 9. Frontend — Components

### `FaceScanner.tsx`
- Requests webcam access via `navigator.mediaDevices.getUserMedia`.
- Captures a frame every few seconds using a canvas element.
- POSTs the base64 image to `/analyze-face`.
- Calls `onEmotionDetected(result)` prop with the detected emotion + confidence.

### `Navbar.tsx`
- Top navigation bar with links to Chat, Journal, Mood Tracker, Resources.
- Includes `ThemeToggle` and `NotificationBell`.
- Responsive — collapses on mobile.

### `NotificationBell.tsx`
- Displays a bell icon with an unread badge count.
- Renders a dropdown of recent notifications.
- Reads from `NotificationsContext`.

### `ThemeToggle.tsx`
- Switches between Light and Dark CSS themes.
- Persists preference to `localStorage`.

---

## 10. Frontend — State & Data Management

### Notifications (`NotificationsContext.tsx`)
- React Context providing `addNotification(title, body, type)` globally.
- Notifications are stored in component state (ephemeral — cleared on page reload).
- Consumed by: `Chat.tsx` (backend error), `MoodTracker.tsx` (mood logged).

### Session ID (`chatbot.ts`)
- Generated once: `${Date.now()}-${randomString}`.
- Stored in `localStorage` as `mindful_chat_session_id`.
- Sent with every `/chat_stream` request so the backend maintains per-user memory.

### Journal & Mood Data
- Stored in `localStorage` under keys `"journalEntries"` and `"moodEntries"`.
- **Not synced to any cloud/database** — privacy by design.

---

## 11. Frontend — API Client (`chatbot.ts`)

### Environment-Aware API URL Resolution
```typescript
const API_BASE_URL =
  VITE_API_BASE_URL ||                     // .env override (highest priority)
  (localhost) ? "http://localhost:5000"    // local dev
             : "https://mindchat-1.onrender.com"; // production fallback
```

### `streamAnalyzeAndRespond()`
The primary function used by `Chat.tsx`:
1. Generates/retrieves session ID from localStorage.
2. POSTs to `/chat_stream` with message + optional `detected_emotion`.
3. Reads the SSE `ReadableStream` with a `TextDecoder`.
4. Parses each `data:` line as JSON.
5. Calls `onMeta(emotion, emoji)` on the first event.
6. Calls `onChunk(text)` for each streaming word chunk.
7. On error: calls `onMeta("Neutral", "🤔")` + `onChunk("I'm having trouble connecting...")` + `onStreamError()`.

### `analyzeAndRespond()`
Legacy non-streaming version. Still available as a fallback if needed.

---

## 12. Phone OTP Authentication (Twilio)

### Backend Flow
1. **`POST /auth/send-otp`**: Generates a 6-digit OTP, stores it in memory (`OTP_STORE[phone]`) with a 5-minute TTL. Sends via Twilio SMS if configured.
2. **`POST /auth/verify-otp`**: Validates OTP + expiry. On success, creates the user in Supabase via the admin REST API (`/auth/v1/admin/users`).

### Frontend Flow (`Login.tsx`)
- Supabase's own `signInWithOtp({ phone })` and `verifyOtp()` methods are used directly (no backend involved for OTP).
- The backend `/auth/send-otp` route is an **alternative** for custom Twilio SMS (used when Supabase phone auth is not configured).

### Twilio Configuration
```env
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+17407592514
```

---

## 13. LLM Configuration & Fallback Chain

| Priority | Provider | Library | Config Key |
|---|---|---|---|
| 1 | GitHub Models (GPT-4o) | LangChain `ChatOpenAI` with custom base_url | `GITHUB_PAT` |
| 2 | Google Gemini 2.5 Flash | LangChain `ChatGoogleGenerativeAI` | `GEMINI_API_KEY` |
| 3 | OpenAI GPT-4o | LangChain `ChatOpenAI` | `OPENAI_API_KEY` |
| 4 | HuggingFace Inference API | Direct HTTP | `HUGGINGFACE_API_KEY` |
| 5 | ML Classifier (offline) | Scikit-Learn `.pkl` | (file-based) |
| 6 | Heuristic Dataset (offline) | JSON lookup | (file-based) |

The backend tries each provider in order. If the primary throws any exception (rate limit, network error, invalid key), it catches and falls through to the next tier — ensuring the app always responds even without internet.

---

## 14. Email Confirmation Template

File: `backend/signup_confirmation_template.html`

- Custom branded HTML email sent by Supabase on signup.
- Uses Supabase template variable `{{ .ConfirmationURL }}` for the confirmation link.
- Design: Green (#2A6E59) header, "Playfair Display" font, gradient accent bar, responsive layout.
- **To activate:** Copy HTML → Supabase Dashboard → Authentication → Email Templates → Confirm signup → paste HTML source → Save.

---

## 15. Technology Stack Summary

| Layer | Technology | Purpose |
|---|---|---|
| Frontend Framework | React 18 + Vite + TypeScript | UI rendering and build tooling |
| Styling | Tailwind CSS + Shadcn UI | Utility-first CSS + accessible components |
| Animations | Framer Motion | Page transitions, message animations |
| Icons | Lucide React | Icon library |
| Charts | Recharts `AreaChart` | Mood trend visualization |
| Date Formatting | date-fns | Human-readable dates in Journal/Mood |
| Auth & Database | Supabase | Authentication + PostgreSQL cloud DB |
| Backend Framework | Flask + Flask-CORS | Python REST API server |
| AI Orchestration | LangChain | Unified LLM interface with prompt templates |
| Primary LLM | Google Gemini 2.5 Flash | Generative AI responses |
| Secondary LLM | GitHub Models GPT-4o | LLM fallback via Azure inference endpoint |
| ML Classifier | Scikit-Learn | Offline emotion classification from text |
| Facial AI | DeepFace + OpenCV | Facial emotion recognition from webcam |
| SMS | Twilio | Phone OTP delivery |
| Streaming | Server-Sent Events (SSE) | Real-time word-by-word response streaming |
| State | React Context API | Global notifications state |
| Local Storage | Browser localStorage | Journal entries, mood data, session ID |

---

## 16. Security Notes

- `SUPABASE_SERVICE_ROLE_KEY` is **only in the backend `.env`**, never exposed to the frontend.
- Frontend only has `VITE_SUPABASE_ANON_KEY` which is safe for client-side use.
- RLS policies on `profiles` ensure users can only access their own data.
- OTP store (`OTP_STORE`) is in-memory — all OTPs are lost on server restart.
- Crisis keywords are hard-coded on the backend — they cannot be bypassed by users.

---

*Generated from full codebase analysis — covers every file, module, class, and route in the project.*
