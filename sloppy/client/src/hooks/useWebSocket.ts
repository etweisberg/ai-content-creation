// src/hooks/useWebSocket.ts
import { useEffect, useRef, useCallback } from "react";
import { io, Socket } from "socket.io-client";

const SOCKET_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  const socketRef = useRef<Socket | null>(null);
  const activeTasksRef = useRef<Set<string>>(new Set());

  const connect = useCallback(() => {
    if (socketRef.current?.connected) return;

    socketRef.current = io(SOCKET_URL, {
      transports: ["websocket", "polling"],
    });

    socketRef.current.on("connect", () => {
      console.log("WebSocket connected");
      onConnect?.();
    });

    socketRef.current.on("disconnect", () => {
      console.log("WebSocket disconnected");
      onDisconnect?.();
    });

    socketRef.current.on("connected", (data) => {
      console.log("Server confirmed connection:", data);
    });

    socketRef.current.on("task_update", (update: TaskUpdate) => {
      console.log("Task update received:", update);
      onTaskUpdate?.(update);
    });

    socketRef.current.on("joined_room", (data) => {
      console.log("Joined task room:", data.task_id);
    });

    socketRef.current.on("left_room", (data) => {
      console.log("Left task room:", data.task_id);
    });
  }, [onConnect, onDisconnect, onTaskUpdate]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      activeTasksRef.current.clear();
    }
  }, []);

  const joinTaskRoom = useCallback((taskId: string) => {
    if (!socketRef.current?.connected) return;

    if (activeTasksRef.current.has(taskId)) {
      console.log("Already listening for task:", taskId);
      return;
    }

    socketRef.current.emit("join_task_room", { task_id: taskId });
    activeTasksRef.current.add(taskId);
    console.log("Joining task room:", taskId);
  }, []);

  const leaveTaskRoom = useCallback((taskId: string) => {
    if (!socketRef.current?.connected) return;

    socketRef.current.emit("leave_task_room", { task_id: taskId });
    activeTasksRef.current.delete(taskId);
    console.log("Leaving task room:", taskId);
  }, []);

  const leaveAllTaskRooms = useCallback(() => {
    activeTasksRef.current.forEach((taskId) => {
      if (socketRef.current?.connected) {
        socketRef.current.emit("leave_task_room", { task_id: taskId });
      }
    });
    activeTasksRef.current.clear();
  }, []);

  useEffect(() => {
    connect();

    return () => {
      leaveAllTaskRooms();
      disconnect();
    };
  }, [connect, disconnect, leaveAllTaskRooms]);

  return {
    socket: socketRef.current,
    connect,
    disconnect,
    joinTaskRoom,
    leaveTaskRoom,
    leaveAllTaskRooms,
    isConnected: socketRef.current?.connected || false,
  };
}
