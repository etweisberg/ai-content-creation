// src/hooks/WebSocket.ts
import { useEffect, useRef, useCallback, useState } from "react";
import { socket, isSocketInstance } from "@/lib/socket";

interface TaskUpdate {
  task_id: string;
  type: "completed" | "failed";
  error?: string;
}

interface UseWebSocketProps {
  onTaskUpdate?: (update: TaskUpdate) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export function useWebSocket({
  onTaskUpdate,
  onConnect,
  onDisconnect,
}: UseWebSocketProps = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const activeTasksRef = useRef<Set<string>>(new Set());
  const isInitializedRef = useRef(false);

  const connect = useCallback(async () => {
    let socketToUse = socket;
    
    if (!isSocketInstance(socketToUse)) {
      console.warn("Socket not available, attempting to initialize...");
      // Wait for socket to initialize if we're in the browser
      if (typeof window !== "undefined") {
        console.log("Waiting for socket to initialize...");
        try {
          // Import the socket promise and wait for it to resolve
          const { socketPromise } = await import("@/lib/socket");
          socketToUse = await socketPromise;
          
          if (!isSocketInstance(socketToUse)) {
            console.error("Socket failed to initialize");
            return;
          }
        } catch (error) {
          console.error("Error initializing socket:", error);
          return;
        }
      } else {
        return;
      }
    }

    if (socketToUse.connected) return;

    // Reset initialization flag if socket is not connected
    // This allows reconnection attempts
    if (!socketToUse.connected) {
      isInitializedRef.current = false;
    }

    if (isInitializedRef.current) return;

    console.log("🔌 Initializing WebSocket connection...");
    isInitializedRef.current = true;

    // Set up event listeners
    socketToUse.on("connect", () => {
      console.log("✅ WebSocket connected");
      setIsConnected(true);

      // Rejoin all active task rooms after reconnection
      activeTasksRef.current.forEach((taskId) => {
        if (socketToUse != null) {
          console.log(`🔄 Rejoining task room: ${taskId}`);
          socketToUse.emit("join_task_room", { task_id: taskId });
        } else {
          console.error("Socket null");
        }
      });

      onConnect?.();
    });

    socketToUse.on("disconnect", () => {
      console.log("❌ WebSocket disconnected");
      setIsConnected(false);
      onDisconnect?.();
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    socketToUse.on("connected", (data: any) => {
      console.log("🎉 Server confirmed connection:", data);
    });

    socketToUse.on("task_update", (update: TaskUpdate) => {
      console.log("📨 Task update received:");
      console.log("   Task ID:", update.task_id);
      console.log("   Type:", update.type);
      console.log("   Error:", update.error);
      console.log("   Active tasks:", Array.from(activeTasksRef.current));
      onTaskUpdate?.(update);
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    socketToUse.on("joined_room", (data: { task_id: any }) => {
      console.log("🚪 Joined task room:", data.task_id);
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    socketToUse.on("left_room", (data: { task_id: any }) => {
      console.log("🚪 Left task room:", data.task_id);
    });

    // Add debugging for any message
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    socketToUse.onAny((eventName: string, ...args: any[]) => {
      console.log(`📡 Socket event '${eventName}':`, args);
    });

    // Connect if not already connected
    if (!socketToUse.connected) {
      socketToUse.connect();
    }

    // Set initial connection state
    setIsConnected(socketToUse.connected);
  }, []); // Empty dependency array!

  const disconnect = useCallback(() => {
    if (!isSocketInstance(socket)) return;

    console.log("🔌 Disconnecting WebSocket...");

    // Leave all task rooms before disconnecting
    activeTasksRef.current.forEach((taskId) => {
      if (socket != null) {
        socket.emit("leave_task_room", { task_id: taskId });
      } else {
        console.error("Socket null");
      }
    });
    activeTasksRef.current.clear();

    // Remove event listeners
    socket.off("connect");
    socket.off("disconnect");
    socket.off("connected");
    socket.off("task_update");
    socket.off("joined_room");
    socket.off("left_room");
    socket.offAny(); // Remove the onAny listener too

    socket.disconnect();
    setIsConnected(false);
    isInitializedRef.current = false;
  }, []);

  const joinTaskRoom = useCallback((taskId: string) => {
    if (!isSocketInstance(socket)) {
      console.warn("❌ Socket not available - cannot join task room:", taskId);
      return;
    }

    if (!socket.connected) {
      console.warn("❌ Socket not connected - cannot join task room:", taskId);
      return;
    }

    if (activeTasksRef.current.has(taskId)) {
      console.log("ℹ️ Already listening for task:", taskId);
      return;
    }

    console.log(`🔗 Joining task room: ${taskId}`);
    socket.emit("join_task_room", { task_id: taskId });
    activeTasksRef.current.add(taskId);

    // Add verification
    console.log(
      "   Active tasks after join:",
      Array.from(activeTasksRef.current)
    );
  }, []);

  const leaveTaskRoom = useCallback((taskId: string) => {
    if (!isSocketInstance(socket)) {
      console.warn("❌ Socket not available - cannot leave task room:", taskId);
      return;
    }

    if (!socket.connected) {
      console.warn("❌ Socket not connected - cannot leave task room:", taskId);
      return;
    }

    console.log(`🚪 Leaving task room: ${taskId}`);
    socket.emit("leave_task_room", { task_id: taskId });
    activeTasksRef.current.delete(taskId);
    console.log(
      "   Active tasks after leave:",
      Array.from(activeTasksRef.current)
    );
  }, []);

  const leaveAllTaskRooms = useCallback(() => {
    if (!isSocketInstance(socket)) return;

    console.log("🧹 Leaving all task rooms");
    activeTasksRef.current.forEach((taskId) => {
      if (socket != null) {
        if (socket.connected) {
          socket.emit("leave_task_room", { task_id: taskId });
        }
      } else {
        console.error("Socket null");
      }
    });
    activeTasksRef.current.clear();
    console.log("✅ Left all task rooms");
  }, []);

  // Initialize connection on mount - RUNS ONLY ONCE!
  useEffect(() => {
    // Only run in browser environment
    if (typeof window === "undefined") return;

    console.log("🚀 WebSocket hook mounting - initializing connection");
    
    // Handle async connect function
    const initializeConnection = async () => {
      try {
        await connect();
      } catch (error) {
        console.error("Failed to initialize connection:", error);
      }
    };
    
    initializeConnection();

    // Cleanup ONLY on component unmount
    return () => {
      console.log("🧹 WebSocket hook unmounting - cleaning up");
      leaveAllTaskRooms();

      if (isSocketInstance(socket)) {
        // Remove only this component's event listeners
        socket.off("connect");
        socket.off("disconnect");
        socket.off("connected");
        socket.off("task_update");
        socket.off("joined_room");
        socket.off("left_room");
        socket.offAny();
      }
    };
  }, []); // EMPTY DEPENDENCY ARRAY - this effect runs only once!

  // Separate effect to handle callback prop changes
  useEffect(() => {
    if (!isSocketInstance(socket) || !isInitializedRef.current) return;

    // Update task_update handler when onTaskUpdate prop changes
    const handleTaskUpdate = (update: TaskUpdate) => {
      console.log("📨 Task update received (updated handler):");
      console.log("   Task ID:", update.task_id);
      console.log("   Type:", update.type);
      console.log("   Error:", update.error);
      onTaskUpdate?.(update);
    };

    // Remove old handler and add new one
    socket.off("task_update");
    socket.on("task_update", handleTaskUpdate);

    return () => {
      socket.off("task_update", handleTaskUpdate);
    };
  }, [onTaskUpdate]); // Only re-run when onTaskUpdate changes

  return {
    socket: isSocketInstance(socket) ? socket : null,
    connect,
    disconnect,
    joinTaskRoom,
    leaveTaskRoom,
    leaveAllTaskRooms,
    isConnected,
  };
}
