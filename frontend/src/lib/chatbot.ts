type EmotionResult = {
  emotion: string;
  emoji: string;
  response: string;
};

const ENV_API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL?.toString()?.replace(/\/+$/, "");
const DEFAULT_PROD_API_BASE_URL = "https://mindchat-3.onrender.com";
const DEFAULT_DEV_API_BASE_URL = "http://127.0.0.1:5000";

const API_BASE_URL =
  ENV_API_BASE_URL ||
  (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? DEFAULT_DEV_API_BASE_URL
    : DEFAULT_PROD_API_BASE_URL);

const emotionPatterns: { keywords: string[]; emotion: string; emoji: string; responses: string[] }[] = [
  {
    keywords: ["stressed", "stress", "overwhelmed", "pressure", "burnout", "exhausted"],
    emotion: "Stress",
    emoji: "😟",
    responses: [
      "I can hear that you're feeling stressed. That's really tough. Let's try a quick breathing exercise: breathe in for 4 counts, hold for 4, and breathe out for 6. How does that feel?",
      "Stress can feel heavy. Remember, it's okay to take a step back. What's one small thing you could do right now to ease the pressure?",
      "You're dealing with a lot. Would you like me to guide you through a grounding exercise? It can help bring you back to the present moment.",
    ],
  },
  {
    keywords: ["anxious", "anxiety", "worried", "nervous", "panic", "fear", "scared"],
    emotion: "Anxiety",
    emoji: "😰",
    responses: [
      "Anxiety can be really overwhelming. Let's ground ourselves: name 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell, and 1 you can taste.",
      "I understand you're feeling anxious. Remember, these feelings are temporary. Try placing your hand on your chest and taking slow, deep breaths.",
      "It sounds like worry is weighing on you. What specific thought keeps coming up? Sometimes naming it can help reduce its power.",
    ],
  },
  {
    keywords: ["sad", "depressed", "down", "unhappy", "hopeless", "lonely", "empty", "crying"],
    emotion: "Sadness",
    emoji: "😢",
    responses: [
      "I'm sorry you're feeling this way. It's okay to feel sad — your feelings are valid. Would you like to talk about what's on your mind?",
      "Feeling down can be isolating, but you're not alone. What's one small thing that has brought you comfort in the past?",
      "Thank you for sharing how you feel. Sadness takes courage to express. I'm here to listen whenever you need.",
    ],
  },
  {
    keywords: ["happy", "good", "great", "wonderful", "amazing", "grateful", "thankful", "joy"],
    emotion: "Happiness",
    emoji: "😊",
    responses: [
      "That's wonderful to hear! What's making you feel this way? Celebrating the good moments is important.",
      "I'm so glad you're feeling good! Take a moment to really soak in this feeling. You deserve it.",
      "That makes me happy too! Gratitude and joy are powerful. What are you most grateful for today?",
    ],
  },
  {
    keywords: ["angry", "mad", "frustrated", "furious", "irritated", "annoyed"],
    emotion: "Anger",
    emoji: "😠",
    responses: [
      "It sounds like something is really bothering you. Anger is a natural emotion. Would you like to talk through what triggered this feeling?",
      "When we feel angry, it often signals an unmet need. What do you think might be underneath this frustration?",
      "I hear you. Try this: clench your fists tightly for 5 seconds, then release. Sometimes physical release helps emotional tension too.",
    ],
  },
  {
    keywords: ["tired", "sleepy", "fatigue", "drained", "no energy"],
    emotion: "Fatigue",
    emoji: "😴",
    responses: [
      "Rest is so important for your mental health. Have you been able to get enough sleep lately?",
      "Feeling drained can affect everything. Consider setting a gentle bedtime routine — even small changes can make a big difference.",
      "Your body might be asking you to slow down. Is there something you could let go of today to give yourself more rest?",
    ],
  },
];

const defaultResponses = [
  "Thank you for sharing. I'm here to listen. Could you tell me more about how you're feeling?",
  "I appreciate you opening up. What emotions are you experiencing right now?",
  "I'm here for you. Sometimes just talking helps. What's been on your mind lately?",
  "Tell me more — I'm listening with no judgement. How has your day been?",
];

export async function analyzeAndRespond(message: string, detectedEmotion?: string): Promise<EmotionResult> {
  // Keep the original function just in case
  try {
    let sessionId = localStorage.getItem("mindful_chat_session_id");
    if (!sessionId) {
      sessionId = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
      localStorage.setItem("mindful_chat_session_id", sessionId);
    }
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId, detected_emotion: detectedEmotion }),
    });
    if (!response.ok) throw new Error('Backend response was not ok');
    return await response.json();
  } catch (error) {
    return { emotion: "Neutral", emoji: "🤔", response: "I'm having trouble connecting to my brain right now..." };
  }
}

export async function streamAnalyzeAndRespond(
  message: string,
  onMeta: (emotion: string, emoji: string) => void,
  onChunk: (chunk: string) => void,
  detectedEmotion?: string
): Promise<void> {
  let sessionId = localStorage.getItem("mindful_chat_session_id");
  if (!sessionId) {
    sessionId = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem("mindful_chat_session_id", sessionId);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/chat_stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId, detected_emotion: detectedEmotion }),
    });
    
    if (!response.ok || !response.body) {
      throw new Error('Backend response was not ok');
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      
      buffer = parts.pop() || '';
      for (const part of parts) {
        if (part.startsWith('data: ')) {
          const dataStr = part.substring(6).trim();
          if (dataStr === '[DONE]') return;
          try {
            const data = JSON.parse(dataStr);
            if (data.type === 'meta') {
              onMeta(data.emotion, data.emoji);
            } else if (data.type === 'chunk') {
              onChunk(data.text);
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e, dataStr);
          }
        }
      }
    }
  } catch (error) {
    console.error('Error in streaming:', error);
    onMeta("Neutral", "🤔");
    onChunk("I'm having trouble connecting to my brain right now.");
  }
}

export const quickPrompts = [
  { label: "I feel stressed", emoji: "😟" },
  { label: "I feel anxious", emoji: "😰" },
  { label: "I feel sad", emoji: "😢" },
  { label: "I feel happy", emoji: "😊" },
  { label: "I need to talk", emoji: "💬" },
];
