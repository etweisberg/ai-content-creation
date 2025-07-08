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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiClient, Script, ScriptState } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";
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

  // WebSocket task update handler
  const handleTaskUpdate = useCallback(
    async (update: {
      task_id: string;
      type: "completed" | "failed";
      error?: string;
    }) => {
      console.log("Task update received:", update);

      if (update.type === "completed") {
        try {
          const updatedScript = await apiClient.getScript(update.task_id);
          setScripts((prev) =>
            prev.map((script) =>
              script.id === update.task_id ? updatedScript : script
            )
          );

          if (selectedScript?.id === update.task_id) {
            setSelectedScript(updatedScript);
          }
        } catch (err) {
          console.error("Failed to refresh script after task completion:", err);
          fetchScripts();
        }
      } else if (update.type === "failed") {
        setError(`Task ${update.task_id} failed: ${update.error}`);
      }

      setActiveTasks((prev) => {
        const newSet = new Set(prev);
        newSet.delete(update.task_id);
        return newSet;
      });
    },
    [selectedScript?.id]
  );

  const { joinTaskRoom, leaveTaskRoom, isConnected } = useWebSocket({
    onTaskUpdate: handleTaskUpdate,
  });

  // Fetch scripts from API
  const fetchScripts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getStudioScripts();
      setScripts(data);

      // Join task rooms for processing scripts
      data.forEach((script) => {
        if (
          [
            ScriptState.GENERATING,
            ScriptState.PRODUCING,
            ScriptState.UPLOADING,
          ].includes(script.state)
        ) {
          joinTaskRoom(script.id);
          setActiveTasks((prev) => new Set(prev).add(script.id));
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch scripts");
    } finally {
      setLoading(false);
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
      joinTaskRoom(response.task_id);
      setActiveTasks((prev) => new Set(prev).add(response.task_id));
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
    }
  };

  const handleScriptUpdate = (updatedScript: Script) => {
    setScripts((prev) =>
      prev.map((script) =>
        script.id === updatedScript.id ? updatedScript : script
      )
    );
    setSelectedScript(updatedScript);

    if (
      [
        ScriptState.GENERATING,
        ScriptState.PRODUCING,
        ScriptState.UPLOADING,
      ].includes(updatedScript.state)
    ) {
      joinTaskRoom(updatedScript.id);
      setActiveTasks((prev) => new Set(prev).add(updatedScript.id));
    }
  };

  const handleScriptDelete = (scriptId: string) => {
    setScripts((prev) => prev.filter((script) => script.id !== scriptId));
    leaveTaskRoom(scriptId);
    setActiveTasks((prev) => {
      const newSet = new Set(prev);
      newSet.delete(scriptId);
      return newSet;
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
  }, []);

  if (loading) {
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
              onClick={fetchScripts}
              variant="ghost"
              size="sm"
              className="text-[#6b7280] hover:bg-[#f1f1f1]"
              disabled={loading}
            >
              <RefreshCw
                className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`}
              />
              Refresh
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
                      stateScripts.map((script) => (
                        <Card
                          key={script.id}
                          className="p-4 hover:bg-[#fafafa] cursor-pointer border-[#e0e0e0] transition-colors relative"
                          onClick={() => handleScriptClick(script)}
                        >
                          {activeTasks.has(script.id) && (
                            <div className="absolute top-2 right-2">
                              <RefreshCw className="w-3 h-3 animate-spin text-[#6366f1]" />
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
                                {script.created_at && (
                                  <span className="text-xs text-[#9ca3af]">
                                    {new Date(
                                      script.created_at
                                    ).toLocaleDateString()}
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-[#1a1a1a] line-clamp-2">
                                {script.user_prompt}
                              </p>
                              {(script.script_cost || script.video_cost) && (
                                <p className="text-xs text-[#6b7280] mt-1">
                                  Cost: $
                                  {(
                                    (script.script_cost || 0) +
                                    (script.video_cost || 0)
                                  ).toFixed(2)}
                                </p>
                              )}
                            </div>
                          </div>
                        </Card>
                      ))
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
      />
    </div>
  );
}
