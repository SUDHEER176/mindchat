import { motion } from "framer-motion";
import { Wind, Phone, BookOpen, Heart, Brain, Smile } from "lucide-react";

const resources = [
  {
    icon: Wind,
    title: "Breathing Exercises",
    description: "Practice calming techniques to reduce stress and anxiety.",
    items: [
      "4-7-8 Breathing: Inhale 4s → Hold 7s → Exhale 8s",
      "Box Breathing: Inhale 4s → Hold 4s → Exhale 4s → Hold 4s",
      "Diaphragmatic Breathing: Breathe deeply into your belly for 5 minutes",
    ],
  },
  {
    icon: Brain,
    title: "Stress Management",
    description: "Evidence-based techniques to manage daily stress.",
    items: [
      "Progressive Muscle Relaxation — tense and release muscle groups",
      "Journaling — write about your thoughts and feelings for 10 minutes",
      "Grounding (5-4-3-2-1) — engage your senses to stay present",
    ],
  },
  {
    icon: Smile,
    title: "Daily Wellness Tips",
    description: "Small habits that make a big difference over time.",
    items: [
      "Get 7-9 hours of sleep each night",
      "Move your body for at least 20 minutes daily",
      "Limit screen time before bed",
      "Practice gratitude — list 3 things you're thankful for",
    ],
  },
  {
    icon: BookOpen,
    title: "Recommended Reading",
    description: "Books and articles that can support your mental health journey.",
    items: [
      '"Feeling Good" by David D. Burns',
      '"The Body Keeps the Score" by Bessel van der Kolk',
      '"Atomic Habits" by James Clear',
    ],
  },
];

const helplines = [
  { name: "National Suicide Prevention Lifeline", number: "988", region: "USA" },
  { name: "Crisis Text Line", number: "Text HOME to 741741", region: "USA" },
  { name: "Samaritans", number: "116 123", region: "UK" },
  { name: "iCall", number: "9152987821", region: "India" },
  { name: "Vandrevala Foundation", number: "1860-2662-345", region: "India" },
];

const Resources = () => {
  return (
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="container mx-auto max-w-5xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 bg-primary/10 text-primary rounded-full px-4 py-1.5 text-sm font-medium mb-6">
            <Heart className="w-4 h-4" />
            Self-care toolkit
          </div>
          <h1 className="font-display text-4xl md:text-5xl font-bold text-foreground mb-4">
            Resources & Support
          </h1>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Evidence-based techniques, helpful tips, and crisis support — all in one place.
          </p>
        </motion.div>

        {/* Resource Cards */}
        <div className="grid md:grid-cols-2 gap-6 mb-16">
          {resources.map((resource, i) => (
            <motion.div
              key={resource.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="bg-card border border-border rounded-2xl p-7"
              style={{ boxShadow: "var(--shadow-soft)" }}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <resource.icon className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-display text-lg font-semibold text-foreground">{resource.title}</h3>
                  <p className="text-xs text-muted-foreground">{resource.description}</p>
                </div>
              </div>
              <ul className="space-y-2.5">
                {resource.items.map((item) => (
                  <li key={item} className="text-sm text-muted-foreground flex gap-2">
                    <span className="text-primary mt-0.5">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>

        {/* Helplines */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="rounded-2xl p-8 border border-border"
          style={{ background: "var(--gradient-calm)" }}
        >
          <div className="flex items-center gap-3 mb-6">
            <Phone className="w-6 h-6 text-primary-foreground" />
            <h2 className="font-display text-2xl font-bold text-primary-foreground">Crisis Helplines</h2>
          </div>
          <p className="text-primary-foreground/80 mb-6">
            If you're in crisis, please reach out. These services are free and confidential.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {helplines.map((hl) => (
              <div key={hl.name} className="bg-primary-foreground/10 backdrop-blur-sm rounded-xl p-4">
                <p className="font-medium text-primary-foreground text-sm">{hl.name}</p>
                <p className="text-primary-foreground font-bold text-lg mt-1">{hl.number}</p>
                <p className="text-primary-foreground/60 text-xs mt-1">{hl.region}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Resources;
