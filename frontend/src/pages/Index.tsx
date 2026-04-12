import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { MessageCircle, Shield, Sparkles, Heart, Leaf, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

const features = [
  {
    icon: MessageCircle,
    title: "Empathetic Conversations",
    description: "Chat anytime with an AI companion trained to listen, understand, and support you.",
  },
  {
    icon: Shield,
    title: "Safe & Private",
    description: "Your conversations are private. No judgement, no sharing — just a safe space for you.",
  },
  {
    icon: Sparkles,
    title: "Personalized Support",
    description: "Get tailored coping strategies, breathing exercises, and wellness tips.",
  },
];

const Index = () => {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="relative pt-32 pb-20 px-4 overflow-hidden" style={{ background: "var(--gradient-hero)" }}>
        <div className="container mx-auto max-w-4xl text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          >
            <div className="inline-flex items-center gap-2 bg-primary/10 text-primary rounded-full px-4 py-1.5 text-sm font-medium mb-8">
              <Leaf className="w-4 h-4" />
              Your mental wellness companion
            </div>
            <h1 className="font-display text-5xl md:text-7xl font-bold text-foreground leading-tight mb-6">
              A calm space<br />
              <span className="text-gradient-calm">for your mind</span>
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
              Talk about how you feel, explore coping strategies, and find peace — all through a gentle, 
              supportive conversation.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/chat">
                <Button size="lg" className="rounded-full px-10 text-base shadow-lg">
                  <MessageCircle className="w-5 h-5 mr-2" />
                  Start Chatting
                </Button>
              </Link>
              <Link to="/resources">
                <Button variant="outline" size="lg" className="rounded-full px-10 text-base">
                  Explore Resources
                </Button>
              </Link>
            </div>
          </motion.div>

          {/* Floating decorative elements */}
          <div className="absolute top-20 left-10 text-primary/10 animate-float">
            <Heart className="w-16 h-16" />
          </div>
          <div className="absolute bottom-10 right-10 text-accent/30 animate-float" style={{ animationDelay: "1s" }}>
            <Sun className="w-12 h-12" />
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 px-4">
        <div className="container mx-auto max-w-5xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground mb-4">
              How MindfulChat helps
            </h2>
            <p className="text-muted-foreground text-lg max-w-xl mx-auto">
              A companion designed with care, empathy, and evidence-based techniques.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.15 }}
                className="bg-card rounded-2xl p-8 shadow-sm hover:shadow-md transition-shadow border border-border"
                style={{ boxShadow: "var(--shadow-card)" }}
              >
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-5">
                  <feature.icon className="w-6 h-6 text-primary" />
                </div>
                <h3 className="font-display text-xl font-semibold text-foreground mb-3">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4">
        <div className="container mx-auto max-w-3xl">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="rounded-3xl p-12 text-center text-primary-foreground"
            style={{ background: "var(--gradient-calm)" }}
          >
            <h2 className="font-display text-3xl md:text-4xl font-bold mb-4">
              Ready to feel better?
            </h2>
            <p className="text-primary-foreground/80 text-lg mb-8 max-w-lg mx-auto">
              Start a conversation today. No sign-up required — just you and a supportive listener.
            </p>
            <Link to="/chat">
              <Button size="lg" variant="secondary" className="rounded-full px-10 text-base font-semibold">
                Begin Your Journey
              </Button>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 px-4">
        <div className="container mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Heart className="w-4 h-4 text-primary fill-primary/20" />
            <span>MindfulChat — Your mental health companion</span>
          </div>
          <div className="flex gap-6">
            <Link to="/resources" className="hover:text-primary transition-colors">Resources</Link>
            <Link to="/chat" className="hover:text-primary transition-colors">Chat</Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Index;
