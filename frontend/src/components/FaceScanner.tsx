import { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Camera, Upload, X, Scan, ImageIcon, AlertCircle } from "lucide-react";

interface FaceScanResult {
  emotion: string;
  emoji: string;
  confidence: number;
  raw: string;
}

interface FaceScannerProps {
  onEmotionDetected: (result: FaceScanResult) => void;
  apiBase?: string;
}

export default function FaceScanner({
  onEmotionDetected,
  apiBase = "http://localhost:5000",
}: FaceScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<FaceScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"camera" | "upload">("upload");
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        closePopup();
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const startCamera = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
    } catch {
      setError("Camera blocked");
      setMode("upload");
    }
  }, []);

  const togglePopup = useCallback(() => {
    if (isOpen) {
      closePopup();
    } else {
      setError(null);
      setResult(null);
      setUploadedImage(null);
      setMode("upload");
      setIsOpen(true);
    }
  }, [isOpen]);

  const closePopup = useCallback(() => {
    stopCamera();
    setIsOpen(false);
    setResult(null);
    setUploadedImage(null);
  }, [stopCamera]);

  const switchMode = useCallback(
    (newMode: "camera" | "upload") => {
      stopCamera();
      setError(null);
      setResult(null);
      setUploadedImage(null);
      setMode(newMode);
      if (newMode === "camera") setTimeout(startCamera, 100);
    },
    [startCamera, stopCamera]
  );

  const analyzeImage = useCallback(
    async (imageData: string) => {
      setScanning(true);
      setError(null);
      try {
        const resp = await fetch(`${apiBase}/analyze-face`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image: imageData }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || "Failed");
        setResult(data as FaceScanResult);
        onEmotionDetected(data as FaceScanResult);
        // auto close on success after a delay
        setTimeout(closePopup, 1500);
      } catch (err: any) {
        setError(err.message || "Retry");
      } finally {
        setScanning(false);
      }
    },
    [apiBase, onEmotionDetected, closePopup]
  );

  const captureFromCamera = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    await analyzeImage(canvas.toDataURL("image/jpeg", 0.7));
  }, [analyzeImage]);

  const handleFileUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async (ev) => {
        const imageData = ev.target?.result as string;
        setUploadedImage(imageData);
        await analyzeImage(imageData);
      };
      reader.readAsDataURL(file);
      e.target.value = "";
    },
    [analyzeImage]
  );

  return (
    <div className="relative" ref={containerRef}>
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={togglePopup}
        type="button"
        className={`flex h-10 w-10 items-center justify-center rounded-full border transition-all ${isOpen ? 'bg-primary text-primary-foreground border-primary shadow-lg shadow-primary/20' : 'bg-background hover:bg-muted border-border text-muted-foreground'}`}
      >
        <Camera size={20} />
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: -12, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            className="absolute bottom-full left-0 mb-2 w-64 bg-card border border-border rounded-xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] p-4 origin-bottom-left"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-foreground">Mood Detection</span>
              <button onClick={closePopup} className="text-muted-foreground hover:text-foreground transition-colors">
                <X size={14} />
              </button>
            </div>

            <div className="flex gap-1 mb-3 p-0.5 bg-muted rounded-lg">
              {(['upload', 'camera'] as const).map(m => (
                <button
                  key={m}
                  onClick={() => switchMode(m)}
                  className={`flex-1 py-1 text-[10px] font-bold rounded-md transition-all ${mode === m ? 'bg-card text-primary shadow-sm' : 'text-muted-foreground'}`}
                >
                  {m === 'upload' ? 'Upload' : 'Camera'}
                </button>
              ))}
            </div>

            <div className="relative aspect-video rounded-lg bg-black overflow-hidden border border-border mb-3 group">
              {mode === 'camera' && (
                <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
              )}
              {mode === 'upload' && (
                <div onClick={() => fileInputRef.current?.click()} className="w-full h-full flex flex-col items-center justify-center cursor-pointer hover:bg-white/5 transition-colors">
                  {uploadedImage ? (
                    <img src={uploadedImage} className="w-full h-full object-cover" />
                  ) : (
                    <div className="flex flex-col items-center text-muted-foreground">
                      <ImageIcon size={20} className="mb-1" />
                      <span className="text-[9px]">Select image</span>
                    </div>
                  )}
                </div>
              )}
              {scanning && (
                <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                  <div className="w-5 h-5 border-2 border-primary/20 border-t-primary animate-spin rounded-full" />
                </div>
              )}
            </div>

            {result ? (
              <div className="flex items-center gap-2 p-2 rounded-lg bg-primary/10 border border-primary/20 mb-3 animate-in fade-in slide-in-from-bottom-1">
                <span className="text-lg">{result.emoji}</span>
                <div className="flex-1">
                  <p className="text-[10px] font-bold text-primary leading-tight">{result.emotion}</p>
                  <p className="text-[8px] text-muted-foreground">{result.confidence.toFixed(0)}% Match</p>
                </div>
              </div>
            ) : error ? (
              <div className="flex items-center gap-1.5 text-destructive mb-3 px-1">
                <AlertCircle size={12} />
                <span className="text-[10px] font-medium leading-tight">{error}</span>
              </div>
            ) : null}

            <button
              type="button"
              disabled={scanning}
              onClick={mode === 'camera' ? captureFromCamera : () => fileInputRef.current?.click()}
              className="w-full py-2 rounded-lg bg-primary text-primary-foreground text-[11px] font-bold hover:brightness-110 transition-all disabled:opacity-50"
            >
              {scanning ? 'Analyzing' : mode === 'camera' ? 'Snap Photo' : 'Choose Photo'}
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
      <canvas ref={canvasRef} className="hidden" />
    </div>
);
}
