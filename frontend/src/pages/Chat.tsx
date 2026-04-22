import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { streamAnalyzeAndRespond, quickPrompts } from "@/lib/chatbot";
import FaceScanner from "@/components/FaceScanner";
import { useNotifications } from "@/contexts/NotificationsContext";

type Message = {
  id: number;
  role: "user" | "bot";
  text: string;
  emotion?: string;
  emoji?: string;
};

const Chat = () => {
  const { addNotification } = useNotifications();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 0,
      role: "bot",
      text: "Hi there! 🌿 I'm MindfulChat, your mental health companion. How are you feeling today? You can type freely or use the quick buttons below.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [lastFaceEmotion, setLastFaceEmotion] = useState<{ emotion: string; emoji: string } | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const sendMessage = (text: string) => {
    if (!text.trim()) return;

    const userMsg: Message = { id: Date.now(), role: "user", text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    const handleResponse = async () => {
      const botId = Date.now() + 1;
      
      // Initialize an empty bot message
      setMessages((prev) => [...prev, { id: botId, role: "bot", text: "" }]);
      
      await streamAnalyzeAndRespond(
        text,
        (emotion, emoji) => {
          setIsTyping(false); // Stop typing loader when we get meta
          setMessages((prev) => prev.map(msg => 
            msg.id === botId ? { ...msg, emotion, emoji } : msg
          ));
        },
        (chunk) => {
          setIsTyping(false);
          setMessages((prev) => prev.map(msg => 
            msg.id === botId ? { ...msg, text: msg.text + chunk } : msg
          ));
        },
        lastFaceEmotion?.emotion,
        () => {
          addNotification({
            title: "Couldn’t reach the chat server",
            body: "Check your connection or try again in a moment.",
            type: "warning",
          });
        }
      );
      
      setLastFaceEmotion(null); // Clear after use
      setIsTyping(false);
    };

    setTimeout(handleResponse, 100);
  };

  const handleFaceEmotion = (result: { emotion: string; emoji: string; confidence: number }) => {
    // Silently store the emotion to be sent with the next user message
    setLastFaceEmotion({ emotion: result.emotion, emoji: result.emoji });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="min-h-screen pt-16 flex flex-col bg-background">
      {/* Chat header */}
      <div className="border-b border-border bg-card/50 backdrop-blur-sm px-4 py-3">
        <div className="container mx-auto max-w-3xl flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
            <Bot className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="font-display text-lg font-semibold text-foreground">MindfulChat</h1>
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse-soft inline-block" />
              Always here for you
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="container mx-auto max-w-3xl space-y-4">
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "bot" && (
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-1">
                    <Bot className="w-4 h-4 text-primary" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground rounded-br-md"
                      : "bg-card text-card-foreground border border-border rounded-bl-md"
                  }`}
                >
                  {/* {msg.emotion && (
                    <span className="inline-block text-xs font-medium bg-primary/10 text-primary rounded-full px-2 py-0.5 mb-2">
                      {msg.emoji} Detected: {msg.emotion}
                    </span>
                  )} */}
                  <p>{msg.text}</p>
                </div>
                {msg.role === "user" && (
                  <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0 mt-1">
                    <User className="w-4 h-4 text-secondary-foreground" />
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {isTyping && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-3 items-start"
            >
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-primary" />
              </div>
              <div className="bg-card border border-border rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </motion.div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      {/* Quick prompts */}
      {messages.length <= 1 && (
        <div className="px-4 pb-2">
          <div className="container mx-auto max-w-3xl">
            <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground">
              <Sparkles className="w-3 h-3" />
              Quick start
            </div>
            <div className="flex flex-wrap gap-2">
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt.label}
                  onClick={() => sendMessage(prompt.label)}
                  className="text-sm bg-card border border-border rounded-full px-4 py-2 hover:bg-secondary transition-colors text-foreground"
                >
                  {prompt.emoji} {prompt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-border bg-card/50 backdrop-blur-sm px-4 py-4">
        <div className="container mx-auto max-w-3xl mb-2">
          {lastFaceEmotion && (
            <motion.div 
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-xs font-medium text-primary mb-2"
            >
              <span>{lastFaceEmotion.emoji} Focused on: {lastFaceEmotion.emotion}</span>
              <button 
                onClick={() => setLastFaceEmotion(null)}
                className="hover:text-destructive transition-colors ml-1"
              >
                ×
              </button>
            </motion.div>
          )}
        </div>
        <form onSubmit={handleSubmit} className="container mx-auto max-w-3xl flex gap-3">
          <FaceScanner onEmotionDetected={handleFaceEmotion} />
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type how you're feeling..."
            className="flex-1 rounded-full bg-background"
            disabled={isTyping}
          />
          <Button type="submit" size="icon" className="rounded-full flex-shrink-0" disabled={!input.trim() || isTyping}>
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  );
};

export default Chat;
