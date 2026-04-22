import { Link, useLocation, useNavigate } from "react-router-dom";
import { Heart, Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import ThemeToggle from "@/components/ThemeToggle";
import NotificationBell from "@/components/NotificationBell";
import { supabase } from "@/lib/supabase";

const navLinks = [
  { to: "/", label: "Home" },
  { to: "/chat", label: "Chat" },
  { to: "/mood", label: "Mood" },
  { to: "/journal", label: "Journal" },
  { to: "/resources", label: "Resources" },
];

const Navbar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [displayName, setDisplayName] = useState<string | null>(null);

  const getAvatarEmoji = (name: string) => {
    const emojis = ["🙂", "😊", "😄", "😎", "🤗", "🌟", "🧠", "💚"];
    const index = name.length % emojis.length;
    return emojis[index];
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setDisplayName(null);
    setMobileOpen(false);
    navigate("/");
  };

  useEffect(() => {
    let mounted = true;

    const setDisplayNameFromUser = (user: any) => {
      const nameFromMetadata = user?.user_metadata?.full_name ?? null;
      const fallback = user?.email ?? user?.phone ?? "User";
      setDisplayName(nameFromMetadata || fallback);
    };

    const loadProfile = async (user: any) => {
      if (!mounted) return;
      if (!user) {
        setDisplayName(null);
        return;
      }

      // Show user identity immediately, then refine from profiles table.
      setDisplayNameFromUser(user);

      const { data: profile } = await supabase
        .from("profiles")
        .select("full_name")
        .eq("id", user.id)
        .single();

      if (!mounted) return;
      const nameFromProfile = profile?.full_name ?? null;
      if (nameFromProfile) {
        setDisplayName(nameFromProfile);
      }
    };

    const initialize = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      await loadProfile(session?.user ?? null);
    };

    initialize();

    const { data: authListener } = supabase.auth.onAuthStateChange((_event, session) => {
      loadProfile(session?.user ?? null);
    });

    return () => {
      mounted = false;
      authListener.subscription.unsubscribe();
    };
  }, []);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
      <div className="container mx-auto flex items-center justify-between h-16 px-4">
        <Link to="/" className="flex items-center gap-2 font-display text-xl font-semibold text-foreground">
          <Heart className="w-6 h-6 text-primary fill-primary/20" />
          MindfulChat
        </Link>

        {/* Desktop */}
        <div className="hidden md:flex items-center gap-6">
          {navLinks.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`text-sm font-medium transition-colors hover:text-primary ${
                location.pathname === link.to ? "text-primary" : "text-muted-foreground"
              }`}
            >
              {link.label}
            </Link>
          ))}
          <NotificationBell />
          <ThemeToggle />
          {displayName ? (
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" className="rounded-full px-4">
                {getAvatarEmoji(displayName)} Hi, {displayName}
              </Button>
              <Button size="sm" variant="ghost" onClick={handleLogout}>
                Log out
              </Button>
            </div>
          ) : (
            <Link to="/login">
              <Button size="sm" className="rounded-full px-6">
                Sign In
              </Button>
            </Link>
          )}
        </div>

        {/* Mobile toggle */}
        <div className="flex items-center gap-2 md:hidden">
          <NotificationBell />
          <ThemeToggle />
          <button className="text-foreground" onClick={() => setMobileOpen(!mobileOpen)}>
            {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-background border-b border-border overflow-hidden"
          >
            <div className="flex flex-col gap-4 p-4">
              {navLinks.map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  onClick={() => setMobileOpen(false)}
                  className={`text-sm font-medium ${
                    location.pathname === link.to ? "text-primary" : "text-muted-foreground"
                  }`}
                >
                  {link.label}
                </Link>
              ))}
              {displayName ? (
                <>
                  <Button size="sm" variant="outline" className="rounded-full w-full">
                    {getAvatarEmoji(displayName)} Hi, {displayName}
                  </Button>
                  <Button size="sm" variant="ghost" className="w-full" onClick={handleLogout}>
                    Log out
                  </Button>
                </>
              ) : (
                <Link to="/login" onClick={() => setMobileOpen(false)}>
                  <Button size="sm" className="rounded-full w-full">Sign In</Button>
                </Link>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
};

export default Navbar;
