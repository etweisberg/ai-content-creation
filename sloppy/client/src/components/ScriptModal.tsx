// src/components/ScriptModal.tsx
"use client";

import { useState } from "react";
import {
  X,
  Trash2,
  Play,
  Upload,
  RefreshCw,
  Pen,
  FileText,
  Camera,
  Video,
  ArrowUp,
  Check,
  DollarSign,
  Volume2,
} from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { Script, ScriptState, apiClient } from "@/lib/api";

interface ScriptModalProps {
  script: Script | null;
  isOpen: boolean;
  onClose: () => void;
  onScriptUpdate: (script: Script) => void;
  onScriptDelete: (scriptId: string) => void;
  onTaskStart: (taskId: string, scriptId: string) => void;
}

const stateConfig = {
  [ScriptState.GENERATING]: {
    icon: Pen,
    label: "Generating",
    color: "text-blue-500",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
  },
  [ScriptState.GENERATED]: {
    icon: FileText,
    label: "Generated",
    color: "text-green-500",
    bgColor: "bg-green-50",
    borderColor: "border-green-200",
  },
  [ScriptState.PRODUCING]: {
    icon: Camera,
    label: "Producing",
    color: "text-orange-500",
    bgColor: "bg-orange-50",
    borderColor: "border-orange-200",
  },
  [ScriptState.PRODUCED]: {
    icon: Video,
    label: "Produced",
    color: "text-purple-500",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-200",
  },
  [ScriptState.UPLOADING]: {
    icon: ArrowUp,
    label: "Uploading",
    color: "text-yellow-500",
    bgColor: "bg-yellow-50",
    borderColor: "border-yellow-200",
  },
  [ScriptState.UPLOADED]: {
    icon: Check,
    label: "Uploaded",
    color: "text-emerald-500",
    bgColor: "bg-emerald-50",
    borderColor: "border-emerald-200",
  },
};

export function ScriptModal({
  script,
  isOpen,
  onClose,
  onScriptUpdate,
  onScriptDelete,
  onTaskStart,
}: ScriptModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  if (!isOpen || !script) return null;

  const config = stateConfig[script.state];
  const StateIcon = config.icon;

  const handleDelete = async () => {
    if (
      !confirm(
        "Are you sure you want to delete this script? This action cannot be undone."
      )
    ) {
      return;
    }

    try {
      setIsDeleting(true);
      await apiClient.deleteScript(script.id);
      onScriptDelete(script.id);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete script");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleGenerateVideo = async (
    generationMode: "audio_only" | "video_only" | "both"
  ) => {
    if (!script.script) {
      setError("No script content available for generation");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      let settings = {};
      if (generationMode === "audio_only") {
        settings = { audio_only: true };
      } else if (generationMode === "video_only") {
        settings = { video_only: true };
      }
      // For 'both' mode, settings remains empty object (default behavior)

      const response = await apiClient.generateVideo(
        script.id,
        script.script,
        settings
      );
      onTaskStart(response.task_id, script.id);
      console.log(`${generationMode} generation started:`, response.task_id);

      // The backend handles state updates, just refresh script data
      const updatedScript = await apiClient.getScript(script.id);
      onScriptUpdate(updatedScript);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to start generation"
      );
    } finally {
      setLoading(false);
      onClose();
    }
  };

  const handleUpload = async () => {
    if (!script.video_file) {
      setError("No video file available for upload");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.uploadTikTok(
        script.id,
        script.video_file
      );
      onTaskStart(response.task_id, script.id);
      console.log("Upload started:", response.task_id);

      // The backend handles state updates, just refresh script data
      const updatedScript = await apiClient.getScript(script.id);
      onScriptUpdate(updatedScript);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start upload");
    } finally {
      setLoading(false);
      onClose();
    }
  };

  const getNextActions = () => {
    switch (script.state) {
      case ScriptState.GENERATED:
        return [
          {
            label: "Generate Audio Only",
            action: () => handleGenerateVideo("audio_only"),
            icon: Volume2,
            disabled: !script.script,
            variant: "outline" as const,
          },
          {
            label: "Generate Video w/ Audio",
            action: () => handleGenerateVideo("both"),
            icon: Play,
            disabled: !script.script,
            variant: "default" as const,
          },
          {
            label: "Generate Video Only",
            action: () => handleGenerateVideo("video_only"),
            icon: Video,
            disabled: !script.script,
            variant: "outline" as const,
          },
        ];
      case ScriptState.PRODUCED:
        return [
          {
            label: "Upload to TikTok",
            action: handleUpload,
            icon: Upload,
            disabled: !script.video_file,
            variant: "default" as const,
          },
        ];
      default:
        return [];
    }
  };

  const nextActions = getNextActions();
  const totalCost = (script.script_cost || 0) + (script.video_cost || 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[#e0e0e0]">
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-lg ${config.bgColor} ${config.borderColor} border`}
            >
              <StateIcon className={`w-5 h-5 ${config.color}`} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#1a1a1a]">
                Script Details
              </h2>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-sm font-mono text-[#6b7280]">
                  {script.id}
                </span>
                <Badge
                  variant="secondary"
                  className={`text-xs ${config.color}`}
                >
                  {config.label}
                </Badge>
              </div>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-[#6b7280] hover:bg-[#f1f1f1]"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          {/* User Prompt */}
          <div>
            <h3 className="text-sm font-medium text-[#1a1a1a] mb-2">
              Original Prompt
            </h3>
            <div className="bg-[#fafafa] rounded-lg p-4 border border-[#e0e0e0]">
              <p className="text-sm text-[#1a1a1a]">{script.user_prompt}</p>
            </div>
          </div>

          {/* Generated Script */}
          {script.script && (
            <div>
              <h3 className="text-sm font-medium text-[#1a1a1a] mb-2">
                Generated Script
              </h3>
              <div className="bg-[#fafafa] rounded-lg p-4 border border-[#e0e0e0] max-h-60 overflow-y-auto">
                <pre className="text-sm text-[#1a1a1a] whitespace-pre-wrap font-sans">
                  {script.script}
                </pre>
              </div>
            </div>
          )}

          {/* Audio Preview */}
          {script.audio_file && (
            <div>
              <h3 className="text-sm font-medium text-[#1a1a1a] mb-2 flex items-center gap-2">
                <Volume2 className="w-4 h-4" />
                Audio Preview
              </h3>
              <div className="bg-[#fafafa] rounded-lg p-4 border border-[#e0e0e0]">
                <audio controls className="w-full" preload="metadata">
                  <source src={script.audio_file} type="audio/mpeg" />
                  <source src={script.audio_file} type="audio/wav" />
                  <source src={script.audio_file} type="audio/ogg" />
                  Your browser does not support the audio element.
                </audio>
                <div className="mt-2">
                  <span className="text-xs text-[#6b7280] font-mono">
                    {script.audio_file}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Video Preview */}
          {script.video_file && (
            <div>
              <h3 className="text-sm font-medium text-[#1a1a1a] mb-2 flex items-center gap-2">
                <Video className="w-4 h-4" />
                Video Preview
              </h3>
              <div className="bg-[#fafafa] rounded-lg p-4 border border-[#e0e0e0]">
                <video
                  controls
                  className="w-full rounded-lg"
                  preload="metadata"
                  style={{ maxHeight: "400px" }}
                >
                  <source
                    src={`/api/av-output/${script.video_file.split("/").pop()}`}
                    type="video/mp4"
                  />
                  <source
                    src={`/api/av-output/${script.video_file.split("/").pop()}`}
                    type="video/webm"
                  />
                  <source
                    src={`/api/av-output/${script.video_file.split("/").pop()}`}
                    type="video/ogg"
                  />
                  Your browser does not support the video element.
                </video>
                <div className="mt-2">
                  <span className="text-xs text-[#6b7280] font-mono">
                    {script.video_file}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Costs */}
          {totalCost > 0 && (
            <div>
              <h3 className="text-sm font-medium text-[#1a1a1a] mb-2">Costs</h3>
              <div className="bg-[#fafafa] rounded-lg p-4 border border-[#e0e0e0]">
                <div className="space-y-2">
                  {(script.script_cost ?? 0) > 0 && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-[#6b7280]">Script Generation</span>
                      <span className="font-medium">
                        ${script.script_cost?.toFixed(2)}
                      </span>
                    </div>
                  )}
                  {(script.video_cost ?? 0) > 0 && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-[#6b7280]">Video Production</span>
                      <span className="font-medium">
                        ${script.video_cost?.toFixed(2)}
                      </span>
                    </div>
                  )}
                  <Separator />
                  <div className="flex items-center justify-between text-sm font-semibold">
                    <span className="text-[#1a1a1a]">Total</span>
                    <span className="flex items-center gap-1">
                      <DollarSign className="w-3 h-3" />
                      {totalCost.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* File Information */}
          {(script.audio_file || script.video_file || script.tiktok_url) && (
            <div>
              <h3 className="text-sm font-medium text-[#1a1a1a] mb-2">
                Files & Links
              </h3>
              <div className="bg-[#fafafa] rounded-lg p-4 border border-[#e0e0e0] space-y-2">
                {script.audio_file && (
                  <div className="text-sm">
                    <span className="text-[#6b7280]">Audio: </span>
                    <span className="font-mono text-xs">
                      {script.audio_file}
                    </span>
                  </div>
                )}
                {script.video_file && (
                  <div className="text-sm">
                    <span className="text-[#6b7280]">Video: </span>
                    <span className="font-mono text-xs">
                      {script.video_file}
                    </span>
                  </div>
                )}
                {script.tiktok_url && (
                  <div className="text-sm">
                    <span className="text-[#6b7280]">TikTok: </span>
                    <a
                      href={script.tiktok_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#6366f1] hover:underline"
                    >
                      {script.tiktok_url}
                    </a>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="border-t border-[#e0e0e0] p-6">
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              onClick={handleDelete}
              disabled={isDeleting}
              className="text-red-600 border-red-200 hover:bg-red-50"
            >
              {isDeleting ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4 mr-2" />
              )}
              {isDeleting ? "Deleting..." : "Delete Script"}
            </Button>

            {nextActions.length > 0 && (
              <div className="flex flex-col gap-2">
                {nextActions.map((action, index) => (
                  <Button
                    key={index}
                    onClick={action.action}
                    disabled={loading || action.disabled}
                    variant={action.variant}
                    className={
                      action.variant === "default"
                        ? "bg-[#6366f1] hover:bg-[#5856eb] text-white"
                        : "border-[#6366f1] text-[#6366f1] hover:bg-[#6366f1] hover:text-white"
                    }
                  >
                    {loading ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <action.icon className="w-4 h-4 mr-2" />
                    )}
                    {loading ? "Processing..." : action.label}
                  </Button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
