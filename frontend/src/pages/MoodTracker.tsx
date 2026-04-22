import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Heart, TrendingUp, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { format } from "date-fns";
import { useNotifications } from "@/contexts/NotificationsContext";

type MoodEntry = {
  date: string;
  mood: number;
  emoji: string;
  label: string;
};

const moodOptions = [
  { emoji: "😢", label: "Terrible", value: 1, color: "hsl(0 65% 55%)" },
  { emoji: "😞", label: "Bad", value: 2, color: "hsl(28 60% 55%)" },
  { emoji: "😐", label: "Okay", value: 3, color: "hsl(40 50% 55%)" },
  { emoji: "🙂", label: "Good", value: 4, color: "hsl(120 35% 50%)" },
  { emoji: "😊", label: "Great", value: 5, color: "hsl(158 40% 45%)" },
];

const MoodTracker = () => {
  const { addNotification } = useNotifications();
  const [entries, setEntries] = useState<MoodEntry[]>(() => {
    const saved = localStorage.getItem("moodEntries");
    return saved ? JSON.parse(saved) : [];
  });
  const [todayLogged, setTodayLogged] = useState(false);

  const today = format(new Date(), "yyyy-MM-dd");

  useEffect(() => {
    localStorage.setItem("moodEntries", JSON.stringify(entries));
    setTodayLogged(entries.some((e) => e.date === today));
  }, [entries, today]);

  const logMood = (option: (typeof moodOptions)[0]) => {
    const entry: MoodEntry = {
      date: today,
      mood: option.value,
      emoji: option.emoji,
      label: option.label,
    };
    setEntries((prev) => {
      const filtered = prev.filter((e) => e.date !== today);
      return [...filtered, entry].sort((a, b) => a.date.localeCompare(b.date));
    });
    addNotification({
      title: "Mood check-in saved",
      body: `You logged ${option.label} ${option.emoji} — thanks for taking a moment for yourself.`,
      type: "success",
    });
  };

  const chartData = entries.slice(-14).map((e) => ({
    date: format(new Date(e.date), "MMM d"),
    mood: e.mood,
    emoji: e.emoji,
  }));

  const streak = (() => {
    let count = 0;
    const d = new Date();
    for (let i = 0; i < 365; i++) {
      const key = format(d, "yyyy-MM-dd");
      if (entries.some((e) => e.date === key)) {
        count++;
        d.setDate(d.getDate() - 1);
      } else break;
    }
    return count;
  })();

  return (
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="container mx-auto max-w-3xl">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
          <div className="inline-flex items-center gap-2 bg-primary/10 text-primary rounded-full px-4 py-1.5 text-sm font-medium mb-6">
            <Heart className="w-4 h-4" />
            Daily check-in
          </div>
          <h1 className="font-display text-4xl md:text-5xl font-bold text-foreground mb-4">Mood Tracker</h1>
          <p className="text-muted-foreground text-lg">Track how you feel each day and see patterns over time.</p>
        </motion.div>

        {/* Streak & Stats */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="bg-card border border-border rounded-2xl p-5 text-center">
            <TrendingUp className="w-6 h-6 text-primary mx-auto mb-2" />
            <p className="text-2xl font-bold text-foreground">{streak}</p>
            <p className="text-xs text-muted-foreground">Day streak</p>
          </div>
          <div className="bg-card border border-border rounded-2xl p-5 text-center">
            <Calendar className="w-6 h-6 text-primary mx-auto mb-2" />
            <p className="text-2xl font-bold text-foreground">{entries.length}</p>
            <p className="text-xs text-muted-foreground">Total entries</p>
          </div>
        </div>

        {/* Mood Selector */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-card border border-border rounded-2xl p-8 mb-8"
        >
          <h2 className="font-display text-xl font-semibold text-foreground mb-2 text-center">
            {todayLogged ? "You've logged today! Update?" : "How are you feeling today?"}
          </h2>
          <p className="text-sm text-muted-foreground text-center mb-6">
            {format(new Date(), "EEEE, MMMM d, yyyy")}
          </p>
          <div className="flex justify-center gap-3 sm:gap-5">
            {moodOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => logMood(option)}
                className="flex flex-col items-center gap-2 group"
              >
                <span className="text-4xl sm:text-5xl transition-transform group-hover:scale-125 group-hover:-translate-y-1">
                  {option.emoji}
                </span>
                <span className="text-xs text-muted-foreground group-hover:text-foreground transition-colors">
                  {option.label}
                </span>
              </button>
            ))}
          </div>
        </motion.div>

        {/* Chart */}
        {chartData.length > 1 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-card border border-border rounded-2xl p-6"
          >
            <h2 className="font-display text-xl font-semibold text-foreground mb-6">Last 14 days</h2>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="moodGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(158 40% 45%)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(158 40% 45%)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="hsl(160 10% 45%)" />
                <YAxis domain={[0, 5]} ticks={[1, 2, 3, 4, 5]} tick={{ fontSize: 12 }} stroke="hsl(160 10% 45%)" />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.[0]) return null;
                    const d = payload[0].payload;
                    return (
                      <div className="bg-card border border-border rounded-lg px-3 py-2 text-sm shadow-lg">
                        <p className="font-medium">{d.date}</p>
                        <p>{d.emoji} Mood: {d.mood}/5</p>
                      </div>
                    );
                  }}
                />
                <Area type="monotone" dataKey="mood" stroke="hsl(158 40% 45%)" fill="url(#moodGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </motion.div>
        )}

        {/* Recent entries */}
        {entries.length > 0 && (
          <div className="mt-8">
            <h2 className="font-display text-xl font-semibold text-foreground mb-4">Recent Entries</h2>
            <div className="space-y-2">
              {entries
                .slice(-7)
                .reverse()
                .map((entry) => (
                  <div
                    key={entry.date}
                    className="bg-card border border-border rounded-xl px-4 py-3 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{entry.emoji}</span>
                      <div>
                        <p className="text-sm font-medium text-foreground">{entry.label}</p>
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(entry.date), "EEEE, MMM d")}
                        </p>
                      </div>
                    </div>
                    <span className="text-sm text-muted-foreground">{entry.mood}/5</span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MoodTracker;
