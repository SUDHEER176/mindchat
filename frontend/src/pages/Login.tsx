import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Heart, Mail, Lock, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { supabase } from "@/lib/supabase";

const Login = () => {
  const navigate = useNavigate();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [usePhone, setUsePhone] = useState(false);
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const persistUserAndGoToDashboard = async (user?: any) => {
    if (user && name?.trim() && !user.user_metadata?.full_name) {
      await supabase.auth.updateUser({
        data: { full_name: name.trim() },
      });
    }

    if (user?.id) {
      const inputName = name.trim();
      const normalizedPhone = phone.replace(/\s+/g, "");
      const fullName = user.user_metadata?.full_name ?? (inputName || null);
      const profilePayload = {
        id: user.id,
        full_name: fullName,
        email: user.email ?? (email || null),
        phone: user.phone ?? (normalizedPhone || null),
      };

      const { error: profileError } = await supabase
        .from("profiles")
        .upsert(profilePayload, { onConflict: "id" });

      if (profileError) {
        console.error("Profile upsert failed:", profileError.message);
      }
    }
    navigate("/chat");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (usePhone) return;
    setLoading(true);
    try {
      if (isSignUp) {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { full_name: name } }
        });
        if (error) throw error;
        toast({ title: 'Check your email', description: 'Confirm your email to complete signup' });
      } else {
        const { data, error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        toast({ title: 'Signed in', description: 'Redirecting to chat...' });
        await persistUserAndGoToDashboard(data?.user);
      }
    } catch (err: any) {
      toast({ title: 'Error', description: String(err.message || err) });
    } finally {
      setLoading(false);
    }
  };

  const sendOtp = async () => {
    if (!phone) {
      toast({ title: 'Phone required', description: 'Enter your phone number' });
      return;
    }
    setLoading(true);
    try {
      const normalizedPhone = phone.replace(/\s+/g, "");
      const { error } = await supabase.auth.signInWithOtp({
        phone: normalizedPhone,
        options: {
          shouldCreateUser: true,
        },
      });
      if (error) throw error;
      setOtpSent(true);
      toast({ title: 'OTP sent', description: 'Check your SMS' });
    } catch (err: any) {
      toast({ title: 'Error', description: String(err.message || err) });
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async () => {
    if (!phone || !otp) {
      toast({ title: 'Missing', description: 'Phone and OTP are required' });
      return;
    }
    setLoading(true);
    try {
      const normalizedPhone = phone.replace(/\s+/g, "");
      const normalizedOtp = otp.trim();
      const { data, error } = await supabase.auth.verifyOtp({
        phone: normalizedPhone,
        token: normalizedOtp,
        type: 'sms',
      });
      if (error) throw error;
      toast({ title: 'Verified', description: 'Signed in successfully' });
      await persistUserAndGoToDashboard(data?.user);
    } catch (err: any) {
      toast({ title: 'Error', description: String(err.message || err) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 pt-16" style={{ background: "var(--gradient-hero)" }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 font-display text-2xl font-bold text-foreground">
            <Heart className="w-7 h-7 text-primary fill-primary/20" />
            MindfulChat
          </Link>
          <p className="text-muted-foreground mt-2">
            {isSignUp ? "Create your account" : "Welcome back"}
          </p>
        </div>

        <div className="bg-card rounded-2xl p-8 border border-border" style={{ boxShadow: "var(--shadow-card)" }}>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="flex items-center gap-3 mb-2">
              <label className={`text-sm font-medium ${!usePhone ? 'text-foreground' : 'text-muted-foreground'}`}>
                <input type="radio" checked={!usePhone} onChange={() => setUsePhone(false)} className="mr-2" /> Email
              </label>
              <label className={`text-sm font-medium ${usePhone ? 'text-foreground' : 'text-muted-foreground'}`}>
                <input type="radio" checked={usePhone} onChange={() => setUsePhone(true)} className="mr-2" /> Phone
              </label>
            </div>

            {isSignUp && (
              <div className="space-y-2">
                <Label htmlFor="name" className="text-sm font-medium text-foreground">Full Name</Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Your name"
                    className="pl-10 rounded-xl"
                  />
                </div>
              </div>
            )}
            {!usePhone ? (
              <>
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-sm font-medium text-foreground">Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      className="pl-10 rounded-xl"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password" className="text-sm font-medium text-foreground">Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="pl-10 rounded-xl"
                    />
                  </div>
                </div>

                <Button type="submit" className="w-full rounded-xl text-base h-11">
                  {isSignUp ? "Create Account" : "Sign In"}
                </Button>
              </>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="phone" className="text-sm font-medium text-foreground">Phone</Label>
                  <div className="relative">
                    <Input
                      id="phone"
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+1555..."
                      className="rounded-xl"
                    />
                  </div>
                </div>

                {!otpSent ? (
                  <Button type="button" onClick={sendOtp} disabled={loading} className="w-full rounded-xl text-base h-11">
                    Send OTP
                  </Button>
                ) : (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="otp" className="text-sm font-medium text-foreground">Enter OTP</Label>
                      <Input
                        id="otp"
                        value={otp}
                        onChange={(e) => setOtp(e.target.value)}
                        placeholder="123456"
                        className="rounded-xl"
                      />
                    </div>
                    <Button type="button" onClick={verifyOtp} disabled={loading} className="w-full rounded-xl text-base h-11">
                      Verify OTP
                    </Button>
                  </>
                )}
              </>
            )}
          </form>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            {isSignUp ? "Already have an account?" : "Don't have an account?"}{" "}
            <button
              onClick={() => setIsSignUp(!isSignUp)}
              className="text-primary font-medium hover:underline"
            >
              {isSignUp ? "Sign In" : "Sign Up"}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default Login;
