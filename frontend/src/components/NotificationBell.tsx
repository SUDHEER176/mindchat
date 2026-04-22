import { formatDistanceToNow } from "date-fns";
import { Bell, CheckCheck, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { useNotifications } from "@/contexts/NotificationsContext";
import { cn } from "@/lib/utils";

export default function NotificationBell() {
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllRead,
    clearAll,
    requestBrowserPermission,
  } = useNotifications();

  const handleEnableBrowser = async () => {
    const p = await requestBrowserPermission();
    if (p === "granted") {
      try {
        new Notification("MindfulChat", {
          body: "You’ll get gentle reminders here when enabled from the app.",
          icon: "/favicon.ico",
        });
      } catch {
        /* ignore */
      }
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative rounded-full"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5 text-muted-foreground" />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 p-0">
        <div className="flex items-center justify-between px-3 py-2 border-b border-border">
          <DropdownMenuLabel className="p-0 text-sm font-semibold">Notifications</DropdownMenuLabel>
          <div className="flex gap-1">
            {notifications.length > 0 && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={(e) => {
                    e.preventDefault();
                    markAllRead();
                  }}
                >
                  <CheckCheck className="h-3.5 w-3.5 mr-1" />
                  Read all
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs text-destructive"
                  onClick={(e) => {
                    e.preventDefault();
                    clearAll();
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5 mr-1" />
                  Clear
                </Button>
              </>
            )}
          </div>
        </div>

        {notifications.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">
            No notifications yet. Check-ins and reminders will appear here.
          </div>
        ) : (
          <ScrollArea className="h-[min(320px,50vh)]">
            <div className="py-1">
              {notifications.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  className={cn(
                    "w-full text-left px-3 py-2.5 border-b border-border/60 last:border-0 hover:bg-muted/50 transition-colors",
                    !n.read && "bg-primary/5",
                  )}
                  onClick={() => markAsRead(n.id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-foreground leading-snug">{n.title}</p>
                    {n.type && (
                      <Badge variant="secondary" className="shrink-0 text-[10px] capitalize">
                        {n.type}
                      </Badge>
                    )}
                  </div>
                  {n.body && (
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{n.body}</p>
                  )}
                  <p className="text-[10px] text-muted-foreground mt-1.5">
                    {formatDistanceToNow(n.createdAt, { addSuffix: true })}
                  </p>
                </button>
              ))}
            </div>
          </ScrollArea>
        )}

        <DropdownMenuSeparator className="m-0" />
        <DropdownMenuItem
          className="cursor-pointer rounded-none py-2.5 text-xs text-muted-foreground focus:text-foreground"
          onSelect={(e) => {
            e.preventDefault();
            handleEnableBrowser();
          }}
        >
          Enable browser notifications (optional)
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
