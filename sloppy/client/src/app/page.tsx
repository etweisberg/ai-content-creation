// src/app/page.tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Pen,
  FileText,
  Camera,
  Video,
  ArrowUp,
  Check,
  Send,
  RefreshCw,
  Home,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiClient, Script, ScriptState } from "@/lib/api";
import { useWebSocket } from "@/hooks/WebSocket";
import { ScriptModal } from "@/components/ScriptModal";

const stateIcons = {
  [ScriptState.GENERATING]: {
    icon: Pen,
    label: "Generating",
    color: "text-blue-500",
  },
  [ScriptState.GENERATED]: {
    icon: FileText,
    label: "Generated",
    color: "text-green-500",
  },
  [ScriptState.PRODUCING]: {
    icon: Camera,
    label: "Producing",
    color: "text-orange-500",
  },
  [ScriptState.PRODUCED]: {
    icon: Video,
    label: "Produced",
    color: "text-purple-500",
  },
  [ScriptState.UPLOADING]: {
    icon: ArrowUp,
    label: "Uploading",
    color: "text-yellow-500",
  },
  [ScriptState.UPLOADED]: {
    icon: Check,
    label: "Uploaded",
    color: "text-emerald-500",
  },
};

export default function StudioPage() {
  // State management
  const [prompt, setPrompt] = useState("");
  const [scripts, setScripts] = useState<Script[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedScript, setSelectedScript] = useState<Script | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeTasks, setActiveTasks] = useState<Set<string>>(new Set());
  const [failedTasks, setFailedTasks] = useState<
    Map<string, { scriptId: string; error: string }>
  >(new Map());
  const [taskToScriptMap, setTaskToScriptMap] = useState<Map<string, string>>(
    new Map()
  );
  const [isRefreshing, setIsRefreshing] = useState(false);

  // WebSocket task update handler
  const handleTaskUpdate = useCallback(
    async (update: {
      task_id: string;
      type: "completed" | "failed";
      error?: string;
    }) => {
      console.log("Task update received:", update);

      const scriptId = taskToScriptMap.get(update.task_id);

      if (update.type === "completed") {
        if (scriptId) {
          try {
            const updatedScript = await apiClient.getScript(scriptId);
            setScripts((prev) =>
              prev.map((script) =>
                script.id === scriptId ? updatedScript : script
              )
            );

            if (selectedScript?.id === scriptId) {
              setSelectedScript(updatedScript);
            }

            // Remove any failed task entries for this script
            setFailedTasks((prev) => {
              const newMap = new Map(prev);
              // Remove all failed tasks for this script
              for (const [taskId, taskInfo] of newMap.entries()) {
                if (taskInfo.scriptId === scriptId) {
                  newMap.delete(taskId);
                }
              }
              return newMap;
            });
          } catch (err) {
            console.error(
              "Failed to refresh script after task completion:",
              err
            );
            fetchScripts();
          }
        }
      } else if (update.type === "failed") {
        if (scriptId) {
          // Add to failed tasks with error message and script association
          setFailedTasks((prev) => {
            const newMap = new Map(prev);
            newMap.set(update.task_id, {
              scriptId: scriptId,
              error: update.error || "Unknown error",
            });
            return newMap;
          });

          // Show error notification
          setError(`Task for script ${scriptId} failed: ${update.error}`);

          // Refresh scripts to get the updated state from backend
          try {
            await fetchScripts(true); // Skip task rooms to avoid double joining
          } catch (err) {
            console.error("Failed to refresh scripts after task failure:", err);
          }
        } else {
          // If we don't know which script this task belongs to, show a generic error
          setError(`Task ${update.task_id} failed: ${update.error}`);
        }
      }

      // Remove from active tasks
      setActiveTasks((prev) => {
        const newSet = new Set(prev);
        newSet.delete(update.task_id);
        return newSet;
      });

      // Clean up task mapping
      setTaskToScriptMap((prev) => {
        const newMap = new Map(prev);
        newMap.delete(update.task_id);
        return newMap;
      });
    },
    [selectedScript?.id, taskToScriptMap]
  );

  const { joinTaskRoom, leaveTaskRoom, isConnected, connect } = useWebSocket({
    onTaskUpdate: handleTaskUpdate,
  });

  // Helper function to track task-to-script relationship
  const trackTask = useCallback((taskId: string, scriptId: string) => {
    setTaskToScriptMap((prev) => {
      const newMap = new Map(prev);
      newMap.set(taskId, scriptId);
      return newMap;
    });
    joinTaskRoom(taskId);
    setActiveTasks((prev) => new Set(prev).add(taskId));
  }, []);

  // Join task rooms for active scripts
  const joinActiveTaskRooms = useCallback(
    (scriptList: Script[]) => {
      scriptList.forEach((script) => {
        if (
          [
            ScriptState.GENERATING,
            ScriptState.PRODUCING,
            ScriptState.UPLOADING,
          ].includes(script.state) &&
          script.active_task_id
        ) {
          // Use the active_task_id to join the WebSocket room
          console.log(
            `Script ${script.id} is in processing state: ${script.state} with active task: ${script.active_task_id}`
          );
          trackTask(script.active_task_id, script.id);
        }
      });
    },
    [trackTask]
  );

  // Fetch scripts from API
  const fetchScripts = useCallback(
    async (skipTaskRooms = false) => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiClient.getStudioScripts();
        setScripts(data);

        // Clean up failed tasks for scripts that are no longer in processing states
        setFailedTasks((prev) => {
          const newMap = new Map();
          prev.forEach((taskInfo, taskId) => {
            const script = data.find((s) => s.id === taskInfo.scriptId);
            // Keep failed task info only if script is still in a processing state
            if (
              script &&
              [
                ScriptState.GENERATING,
                ScriptState.PRODUCING,
                ScriptState.UPLOADING,
              ].includes(script.state)
            ) {
              newMap.set(taskId, taskInfo);
            }
          });
          return newMap;
        });

        // Only join task rooms if not skipping (used during refresh to avoid double joining)
        if (!skipTaskRooms) {
          joinActiveTaskRooms(data);
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to fetch scripts"
        );
      } finally {
        setLoading(false);
      }
    },
    [joinActiveTaskRooms]
  );

  // Get failed tasks for a specific script
  const getScriptFailedTasks = useCallback(
    (scriptId: string) => {
      const scriptFailedTasks = [];
      for (const [taskId, taskInfo] of failedTasks.entries()) {
        if (taskInfo.scriptId === scriptId) {
          scriptFailedTasks.push({ taskId, error: taskInfo.error });
        }
      }
      return scriptFailedTasks;
    },
    [failedTasks]
  );

  // Check if a script has any failed tasks
  const scriptHasFailedTasks = useCallback(
    (scriptId: string) => {
      for (const [, taskInfo] of failedTasks.entries()) {
        if (taskInfo.scriptId === scriptId) {
          return true;
        }
      }
      return false;
    },
    [failedTasks]
  );

  // Enhanced refresh that handles WebSocket reconnection
  const handleRefresh = async () => {
    try {
      setIsRefreshing(true);
      setError(null);

      // First, fetch the latest scripts
      const data = await apiClient.getStudioScripts();
      setScripts(data);

      // Clear failed tasks on refresh
      setFailedTasks(new Map());
      setTaskToScriptMap(new Map());

      // If WebSocket is not connected, attempt to reconnect
      if (!isConnected) {
        console.log("WebSocket not connected, attempting to reconnect...");
        try {
          connect();
          console.log("WebSocket reconnection initiated");
        } catch (reconnectError) {
          console.error("Failed to reconnect WebSocket:", reconnectError);
          setError(
            "Failed to reconnect to real-time updates. Some features may not work properly."
          );
        }
      }

      // Clear existing active tasks and rejoin rooms for processing scripts
      setActiveTasks(new Set());

      // Wait a moment for WebSocket to potentially connect before joining rooms
      setTimeout(() => {
        joinActiveTaskRooms(data);
      }, 500);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to refresh scripts"
      );
    } finally {
      setIsRefreshing(false);
    }
  };

  // Event handlers
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isSubmitting) return;

    try {
      setIsSubmitting(true);
      setError(null);

      const response = await apiClient.generateScript(prompt.trim());

      // For script generation, the task_id IS the script ID
      trackTask(response.task_id, response.task_id);
      setPrompt("");
      await fetchScripts();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to generate script"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleScriptClick = async (script: Script) => {
    try {
      const freshScript = await apiClient.getScript(script.id);
      setSelectedScript(freshScript);
      setIsModalOpen(true);
    } catch (err) {
      setError("Failed to load script details");
      console.error(err);
    }
  };

  const handleScriptUpdate = (updatedScript: Script) => {
    setScripts((prev) =>
      prev.map((script) =>
        script.id === updatedScript.id ? updatedScript : script
      )
    );
    setSelectedScript(updatedScript);

    // Note: For actions triggered from the modal (like video generation or upload),
    // the modal component should call trackTask with the new task ID and script ID
  };

  const handleScriptDelete = (scriptId: string) => {
    setScripts((prev) => prev.filter((script) => script.id !== scriptId));

    // Clean up all task-related state for this script
    setActiveTasks((prev) => {
      const newSet = new Set(prev);
      // Remove all tasks associated with this script
      for (const [taskId, mappedScriptId] of taskToScriptMap.entries()) {
        if (mappedScriptId === scriptId) {
          newSet.delete(taskId);
          leaveTaskRoom(taskId);
        }
      }
      return newSet;
    });

    setFailedTasks((prev) => {
      const newMap = new Map(prev);
      // Remove all failed tasks for this script
      for (const [taskId, taskInfo] of newMap.entries()) {
        if (taskInfo.scriptId === scriptId) {
          newMap.delete(taskId);
        }
      }
      return newMap;
    });

    setTaskToScriptMap((prev) => {
      const newMap = new Map(prev);
      // Remove all task mappings for this script
      for (const [taskId, mappedScriptId] of newMap.entries()) {
        if (mappedScriptId === scriptId) {
          newMap.delete(taskId);
        }
      }
      return newMap;
    });
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedScript(null);
  };

  // Group scripts by state
  const scriptsByState = scripts.reduce((acc, script) => {
    if (!acc[script.state]) acc[script.state] = [];
    acc[script.state].push(script);
    return acc;
  }, {} as Record<ScriptState, Script[]>);

  // Load scripts on mount
  useEffect(() => {
    fetchScripts();
  }, [fetchScripts]);

  if (loading && !isRefreshing) {
    return (
      <div className="flex flex-col h-full bg-white">
        <div className="border-b border-[#e0e0e0] p-6">
          <div className="flex items-center gap-3">
            <Home className="w-6 h-6 text-[#6366f1]" />
            <h1 className="text-2xl font-semibold text-[#1a1a1a]">Studio</h1>
          </div>
          <p className="text-[#6b7280] mt-2">
            Generate and manage your video scripts
          </p>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-2 text-[#6b7280]">
            <RefreshCw className="w-4 h-4 animate-spin" />
            <span>Loading scripts...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <header className="border-b border-[#e0e0e0] p-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <Home className="w-6 h-6 text-[#6366f1]" />
              <h1 className="text-2xl font-semibold text-[#1a1a1a]">Studio</h1>
            </div>
            <p className="text-[#6b7280] mt-2">
              Generate and manage your video scripts
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 text-xs text-[#6b7280]">
              <div
                className={`w-2 h-2 rounded-full ${
                  isConnected ? "bg-green-500" : "bg-red-500"
                }`}
              />
              {isConnected ? "Connected" : "Disconnected"}
            </div>
            <Button
              onClick={handleRefresh}
              variant="ghost"
              size="sm"
              className="text-[#6b7280] hover:bg-[#f1f1f1]"
              disabled={loading || isRefreshing}
            >
              <RefreshCw
                className={`w-4 h-4 mr-2 ${
                  loading || isRefreshing ? "animate-spin" : ""
                }`}
              />
              {isRefreshing ? "Refreshing..." : "Refresh"}
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-auto p-6 space-y-8">
        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700 text-sm">{error}</p>
            <Button
              onClick={() => setError(null)}
              variant="ghost"
              size="sm"
              className="mt-2 text-red-700 hover:bg-red-100"
            >
              Dismiss
            </Button>
          </div>
        )}

        {/* WebSocket Status Warning */}
        {!isConnected && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-yellow-700 text-sm">
              ⚠️ Real-time updates are currently unavailable. Click refresh to
              reconnect and get the latest updates.
            </p>
          </div>
        )}

        {/* Script Generation Form */}
        <section className="bg-[#fafafa] rounded-lg border border-[#e0e0e0] p-6">
          <h2 className="text-lg font-semibold text-[#1a1a1a] mb-4">
            Generate New Script
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="prompt"
                className="block text-sm font-medium text-[#1a1a1a] mb-2"
              >
                Script Prompt
              </label>
              <textarea
                id="prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe the video script you want to generate..."
                className="w-full min-h-[120px] p-3 border border-[#e0e0e0] rounded-md focus:outline-none focus:ring-2 focus:ring-[#6366f1] focus:border-transparent resize-none"
                required
                disabled={isSubmitting}
              />
            </div>
            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={!prompt.trim() || isSubmitting}
                className="bg-[#6366f1] hover:bg-[#5856eb] text-white"
              >
                {isSubmitting ? (
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Send className="w-4 h-4 mr-2" />
                )}
                {isSubmitting ? "Generating..." : "Generate Script"}
              </Button>
            </div>
          </form>
        </section>

        {/* Script Pipeline */}
        <section className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {Object.values(ScriptState)
            .filter(
              (state) =>
                typeof state === "number" && state !== ScriptState.UPLOADED
            )
            .map((state) => {
              const config = stateIcons[state as ScriptState];
              const stateScripts = scriptsByState[state as ScriptState] || [];
              const StateIcon = config.icon;

              return (
                <div key={state} className="space-y-4">
                  {/* Section Header */}
                  <div className="flex items-center gap-3">
                    <StateIcon className={`w-5 h-5 ${config.color}`} />
                    <h3 className="font-semibold text-[#1a1a1a]">
                      {config.label}
                    </h3>
                    <Badge variant="secondary" className="text-xs">
                      {stateScripts.length}
                    </Badge>
                  </div>

                  {/* Scripts List */}
                  <div className="space-y-3">
                    {stateScripts.length === 0 ? (
                      <Card className="p-4 border-dashed border-[#e0e0e0] bg-[#fafafa]">
                        <p className="text-sm text-[#6b7280] text-center">
                          No scripts in this stage
                        </p>
                      </Card>
                    ) : (
                      stateScripts.map((script) => {
                        const scriptFailedTasks = getScriptFailedTasks(
                          script.id
                        );
                        const hasActiveTasks =
                          script.active_task_id &&
                          activeTasks.has(script.active_task_id);

                        return (
                          <Card
                            key={script.id}
                            className="p-4 hover:bg-[#fafafa] cursor-pointer border-[#e0e0e0] transition-colors relative"
                            onClick={() => handleScriptClick(script)}
                          >
                            {/* Active Task Indicator */}
                            {hasActiveTasks && (
                              <div className="absolute top-2 right-2">
                                <RefreshCw className="w-3 h-3 animate-spin text-[#6366f1]" />
                              </div>
                            )}

                            {/* Failed Task Indicator */}
                            {scriptHasFailedTasks(script.id) && (
                              <div
                                className="absolute top-2 right-2"
                                title={`Failed tasks: ${scriptFailedTasks
                                  .map((t) => t.error)
                                  .join(", ")}`}
                              >
                                <AlertCircle className="w-3 h-3 text-red-500" />
                              </div>
                            )}

                            <div className="flex items-start gap-3">
                              <StateIcon
                                className={`w-4 h-4 mt-1 ${config.color} flex-shrink-0`}
                              />
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-sm font-mono text-[#6b7280]">
                                    {script.id}
                                  </span>
                                  {/* Failed task badge */}
                                  {scriptHasFailedTasks(script.id) && (
                                    <Badge
                                      variant="destructive"
                                      className="text-xs"
                                    >
                                      Failed Tasks
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-sm text-[#1a1a1a] line-clamp-2">
                                  {script.user_prompt}
                                </p>
                                {/* Show error messages for failed tasks */}
                                {scriptFailedTasks.length > 0 && (
                                  <div className="mt-1 space-y-1">
                                    {scriptFailedTasks.map(
                                      (failedTask, index) => (
                                        <p
                                          key={index}
                                          className="text-xs text-red-600 italic"
                                        >
                                          Task failed: {failedTask.error}
                                        </p>
                                      )
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          </Card>
                        );
                      })
                    )}
                  </div>
                </div>
              );
            })}
        </section>
      </main>

      {/* Script Modal */}
      <ScriptModal
        script={selectedScript}
        isOpen={isModalOpen}
        onClose={closeModal}
        onScriptUpdate={handleScriptUpdate}
        onScriptDelete={handleScriptDelete}
        onTaskStart={trackTask} // Pass the trackTask function to the modal
      />
    </div>
  );
}
