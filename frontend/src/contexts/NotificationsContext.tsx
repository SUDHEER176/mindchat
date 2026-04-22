import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { toast } from "@/components/ui/sonner";

const STORAGE_KEY = "mindful_notifications_v1";
const MAX_ITEMS = 50;

export type AppNotificationType = "info" | "success" | "reminder" | "warning";

export type AppNotification = {
  id: string;
  title: string;
  body?: string;
  read: boolean;
  createdAt: number;
  type?: AppNotificationType;
};

type AddOptions = {
  title: string;
  body?: string;
  type?: AppNotificationType;
  /** Show Sonner toast immediately (default true) */
  showToast?: boolean;
  /** If true, also fire browser Notification when permission granted */
  browser?: boolean;
};

type NotificationsContextValue = {
  notifications: AppNotification[];
  unreadCount: number;
  addNotification: (opts: AddOptions) => void;
  markAsRead: (id: string) => void;
  markAllRead: () => void;
  remove: (id: string) => void;
  clearAll: () => void;
  requestBrowserPermission: () => Promise<NotificationPermission>;
};

const NotificationsContext = createContext<NotificationsContextValue | null>(null);

function loadFromStorage(): AppNotification[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as AppNotification[];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (n) =>
        n &&
        typeof n.id === "string" &&
        typeof n.title === "string" &&
        typeof n.read === "boolean" &&
        typeof n.createdAt === "number",
    );
  } catch {
    return [];
  }
}

function saveToStorage(items: AppNotification[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    /* ignore quota */
  }
}

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<AppNotification[]>(() =>
    typeof window !== "undefined" ? loadFromStorage() : [],
  );

  useEffect(() => {
    saveToStorage(notifications);
  }, [notifications]);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.read).length,
    [notifications],
  );

  const addNotification = useCallback((opts: AddOptions) => {
    const {
      title,
      body,
      type = "info",
      showToast = true,
      browser = false,
    } = opts;

    const item: AppNotification = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      title,
      body,
      read: false,
      createdAt: Date.now(),
      type,
    };

    setNotifications((prev) => {
      const next = [item, ...prev].slice(0, MAX_ITEMS);
      return next;
    });

    if (showToast) {
      if (body) {
        toast(title, { description: body });
      } else {
        toast(title);
      }
    }

    if (browser && typeof Notification !== "undefined" && Notification.permission === "granted") {
      try {
        new Notification(title, { body: body || undefined, icon: "/favicon.ico" });
      } catch {
        /* ignore */
      }
    }
  }, []);

  const markAsRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
    );
  }, []);

  const markAllRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const remove = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const requestBrowserPermission = useCallback(async () => {
    if (typeof Notification === "undefined") return "denied";
    if (Notification.permission === "granted") return "granted";
    if (Notification.permission === "denied") return "denied";
    return Notification.requestPermission();
  }, []);

  const value = useMemo<NotificationsContextValue>(
    () => ({
      notifications,
      unreadCount,
      addNotification,
      markAsRead,
      markAllRead,
      remove,
      clearAll,
      requestBrowserPermission,
    }),
    [
      notifications,
      unreadCount,
      addNotification,
      markAsRead,
      markAllRead,
      remove,
      clearAll,
      requestBrowserPermission,
    ],
  );

  return (
    <NotificationsContext.Provider value={value}>
      {children}
    </NotificationsContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationsContext);
  if (!ctx) {
    throw new Error("useNotifications must be used within NotificationsProvider");
  }
  return ctx;
}
