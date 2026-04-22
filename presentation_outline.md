# 🌿 Mindful Companion: Project Presentation Outline

This document provides a detailed slide-by-slide content breakdown for the Mindful Companion (MindfulChat) project presentation.

---

## 📽️ Slide Overview

### Slide 1: Title Slide
*   **Main Title:** Mindful Companion (MindfulChat)
*   **Subtitle:** Empathetic AI for Emotional Well-being
*   **Key Highlights:** 
    *   AI × Mental Health
    *   Real-time Facial Emotion Recognition
    *   Multi-Model Hybrid Intelligence
*   **Top Tags:** 🎭 DeepFace Vision | 🧠 LangChain LLM | ⚡ Real-time SSE | 🛡️ Crisis Safety

---

### Slide 2: Problem Statement
*   **Heading:** The Mental Health Accessibility Crisis
*   **Content:**
    *   **970 Million People:** Globally living with mental health disorders; most lack professional care.
    *   **Text-Only Bots Fail:** Traditional chatbots lack emotional awareness and miss non-verbal cues.
    *   **24/7 Gap:** Human support is limited by cost and time; digital tools often feel "robotic."

---

### Slide 3: Objective
*   **Goal:** To build an AI platform that fuses **Computer Vision** and **Generative AI** to create an empathetic, always-available wellness space.
*   **Primary Objectives:**
    *   Emotion-aware chat that adapts tone to facial expressions.
    *   100% uptime via a three-tier AI fail-safe architecture.
    *   Strict clinical safety guardrails.
    *   Holistic toolkit: tracking, journaling, and resources.

---

### Slide 4: SDLC Model (Agile)
*   **Framework:** Agile Scrum (2-week sprints, 12-week total timeline).
*   **Sprint Breakdown:**
    *   **Sprint 1:** Foundation & Backend Setup.
    *   **Sprint 2:** Core AI Intelligence (LLM + ML).
    *   **Sprint 3:** Vision AI (DeepFace Integration).
    *   **Sprint 4:** Safety Guardrails & UX Polish.
    *   **Sprint 5:** Rigorous Testing & QA.
    *   **Sprint 6:** Deployment & Final Documentation.

---

### Slide 5: Functional Requirements
*   **FR-01:** Real-time conversational interface with SSE streaming.
*   **FR-02:** Facial emotion detection using DeepFace during chat.
*   **FR-03:** Prompt "injection" where emotion modifies AI response tone.
*   **FR-04:** Immediate crisis detection and redirect system.
*   **FR-05:** Scope guardrails to filter non-mental health queries.
*   **FR-06:** Mood tracking and digital journaling dashboards.

---

### Slide 6: Non-Functional Requirements
*   **Performance:** < 400ms SSE latency; < 1.5s emotion inference.
*   **Availability:** 100% uptime via heuristic fallback.
*   **Privacy:** Zero frame storage; frames processed in-memory only.
*   **Security:** API key protection via `.env` and secure CORS.
*   **Usability:** Mobile-responsive design with "Premium" dark-mode aesthetics.

---

### Slide 7: System Architecture
*   **User Interface:** React (Vite) capturing text and video.
*   **Backend:** Flask Controller managing the flow.
*   **Vision Engine:** DeepFace analyzing local frames for emotion.
*   **AI Orchestrator:** Priority chain -> Cloud LLM (Gemini) -> Local ML -> Heuristic JSON.
*   **Data Flow:** SSE Stream for real-time text delivery.

---

### Slide 8: Technology Stack
*   **Frontend:** React, TypeScript, Tailwind CSS, Framer Motion, Shadcn UI.
*   **Backend:** Flask, Python 3.10+, Gunicorn, SSE.
*   **AI/ML:** LangChain, Google Gemini, Scikit-Learn, DeepFace, OpenCV.
*   **Data:** JSON-driven Heuristic Model, Local Pickle files for ML.

---

### Slide 9: Models Used
*   **Tier 1 (LLM):** Google Gemini 1.5 Flash (Primary logic provider).
*   **Tier 2 (ML):** Scikit-Learn Classifier (Local fallback trained on dataset).
*   **Tier 3 (Heuristic):** Pattern Matching via `MentalHealthChatbotDataset.json`.
*   **Vision Model:** DeepFace DNN for classification of 7 emotion states.

---

### Slide 10: Dataset
*   **File:** `MentalHealthChatbotDataset.json`.
*   **Structure:** Intents (tags, patterns, responses).
*   **Labels:** Sadness, Anxiety, Stress, Anger, Happiness, Grief, Neutral.
*   **Stats:** ~950KB knowledge base; ~4MB trained ML pickle.

---

### Slide 11: System Workflow
1.  **Input:** User Message + Facial Capture.
2.  **Safety Check:** Scope and Crisis scanning (Immediate override if unsafe).
3.  **Context Injection:** "User looks [Emotion]. Speak with [Tone]."
4.  **Generation:** Orchestrator picks best available Tier (1, 2, or 3).
5.  **Output:** Token-by-token SSE stream to UI.

---

### Slide 12: Key Modules
*   **ModelManager:** The heart of the backend logic.
*   **FaceScanner.tsx:** Real-time webcam integration component.
*   **Chat.tsx:** Main conversational hub with emotion feedback.
*   **Safety Guard:** Hard-coded keyword scanning & de-escalation logic.
*   **Mood Graph:** Recharts-based emotional trends visualization.

---

### Slide 13: Testing
*   **Unit Testing:** Validating <code>_safety_override()</code> and <code>HeuristicModel</code> logic.
*   **Integration Testing:** Testing SSE stream and webcam connectivity to Flask.
*   **Safety Testing:** Attempting "Unsafe" prompts to verify 100% trigger rate.
*   **UI/UX Testing:** Cross-browser responsive design verification.

---

### Slide 14: Challenges & Future Scope
*   **Current Challenges:** DeepFace latency (Fixed: async frames), ML Misclassification (Fixed: intro-guardrails).
*   **Future Scope (Roadmap):**
    *   🎙️ Voice Synthesis (TTS).
    *   ⌚ Wearable Integration (Heart Rate Sync).
    *   📊 Advanced Therapist Progress Dashboard.

---

### Slide 15: Conclusion
*   **Summary:** Mindful Companion bridges the mental health care gap using synergy between Vision and Generative AI.
*   **Key Takeaways:** 
    *   Emotionally aware responses are more effective.
    *   Privacy-first design builds user trust.
    *   Multi-tier architecture ensures reliable health support.

---

### Slide 16: Closing & Q&A
*   **Closing Quote:** "Empowering emotional well-being through empathetic technology."
*   **Connect:** Project Repo, Demo Link, Team Contacts.
*   **Final Badges:** ⚛️ React | 🐍 Flask | ✨ Gemini | 😊 DeepFace
