import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BookOpen, Plus, Trash2, ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { format } from "date-fns";

type JournalEntry = {
  id: string;
  date: string;
  title: string;
  content: string;
  mood?: string;
};

const moodEmojis = ["😊", "🙂", "😐", "😔", "😢", "😤", "😴", "🤗"];

const Journal = () => {
  const [entries, setEntries] = useState<JournalEntry[]>(() => {
    const saved = localStorage.getItem("journalEntries");
    return saved ? JSON.parse(saved) : [];
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newMood, setNewMood] = useState<string>("");

  useEffect(() => {
    localStorage.setItem("journalEntries", JSON.stringify(entries));
  }, [entries]);

  const createEntry = () => {
    if (!newContent.trim()) return;
    const entry: JournalEntry = {
      id: Date.now().toString(),
      date: new Date().toISOString(),
      title: newTitle.trim() || format(new Date(), "EEEE, MMMM d"),
      content: newContent.trim(),
      mood: newMood || undefined,
    };
    setEntries((prev) => [entry, ...prev]);
    setNewTitle("");
    setNewContent("");
    setNewMood("");
    setIsCreating(false);
  };

  const deleteEntry = (id: string) => {
    setEntries((prev) => prev.filter((e) => e.id !== id));
    if (selectedId === id) setSelectedId(null);
  };

  const selectedEntry = entries.find((e) => e.id === selectedId);

  return (
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="container mx-auto max-w-3xl">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
          <div className="inline-flex items-center gap-2 bg-primary/10 text-primary rounded-full px-4 py-1.5 text-sm font-medium mb-6">
            <BookOpen className="w-4 h-4" />
            Private space
          </div>
          <h1 className="font-display text-4xl md:text-5xl font-bold text-foreground mb-4">Journal</h1>
          <p className="text-muted-foreground text-lg">Write freely. Reflect. Grow. Your entries stay private on this device.</p>
        </motion.div>

        <AnimatePresence mode="wait">
          {/* View single entry */}
          {selectedEntry ? (
            <motion.div key="view" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <Button variant="ghost" className="mb-4" onClick={() => setSelectedId(null)}>
                <ChevronLeft className="w-4 h-4 mr-1" /> Back
              </Button>
              <div className="bg-card border border-border rounded-2xl p-8">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="font-display text-2xl font-semibold text-foreground">
                      {selectedEntry.mood && <span className="mr-2">{selectedEntry.mood}</span>}
                      {selectedEntry.title}
                    </h2>
                    <p className="text-sm text-muted-foreground mt-1">
                      {format(new Date(selectedEntry.date), "EEEE, MMMM d, yyyy 'at' h:mm a")}
                    </p>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => deleteEntry(selectedEntry.id)}>
                    <Trash2 className="w-4 h-4 text-destructive" />
                  </Button>
                </div>
                <p className="text-foreground leading-relaxed whitespace-pre-wrap">{selectedEntry.content}</p>
              </div>
            </motion.div>
          ) : isCreating ? (
            /* Create entry */
            <motion.div key="create" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <Button variant="ghost" className="mb-4" onClick={() => setIsCreating(false)}>
                <ChevronLeft className="w-4 h-4 mr-1" /> Back
              </Button>
              <div className="bg-card border border-border rounded-2xl p-8 space-y-5">
                <div>
                  <label className="text-sm font-medium text-foreground mb-1.5 block">How are you feeling?</label>
                  <div className="flex gap-2 flex-wrap">
                    {moodEmojis.map((emoji) => (
                      <button
                        key={emoji}
                        onClick={() => setNewMood(newMood === emoji ? "" : emoji)}
                        className={`text-2xl p-2 rounded-lg transition-all ${
                          newMood === emoji ? "bg-primary/10 scale-110" : "hover:bg-secondary"
                        }`}
                      >
                        {emoji}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground mb-1.5 block">Title (optional)</label>
                  <Input
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder={format(new Date(), "EEEE, MMMM d")}
                    className="bg-background"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground mb-1.5 block">What's on your mind?</label>
                  <Textarea
                    value={newContent}
                    onChange={(e) => setNewContent(e.target.value)}
                    placeholder="Write your thoughts here..."
                    rows={8}
                    className="bg-background resize-none"
                  />
                </div>
                <Button onClick={createEntry} disabled={!newContent.trim()} className="rounded-full px-8">
                  Save Entry
                </Button>
              </div>
            </motion.div>
          ) : (
            /* Entry list */
            <motion.div key="list" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <Button onClick={() => setIsCreating(true)} className="rounded-full px-6 mb-6">
                <Plus className="w-4 h-4 mr-2" /> New Entry
              </Button>

              {entries.length === 0 ? (
                <div className="bg-card border border-border rounded-2xl p-12 text-center">
                  <BookOpen className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
                  <h3 className="font-display text-xl font-semibold text-foreground mb-2">No entries yet</h3>
                  <p className="text-muted-foreground">Start writing to capture your thoughts and feelings.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {entries.map((entry, i) => (
                    <motion.button
                      key={entry.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      onClick={() => setSelectedId(entry.id)}
                      className="w-full text-left bg-card border border-border rounded-xl px-5 py-4 hover:bg-secondary/50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {entry.mood && <span className="text-xl">{entry.mood}</span>}
                          <div>
                            <p className="font-medium text-foreground text-sm">{entry.title}</p>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {format(new Date(entry.date), "MMM d, yyyy")}
                            </p>
                          </div>
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground mt-2 line-clamp-2">{entry.content}</p>
                    </motion.button>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default Journal;
