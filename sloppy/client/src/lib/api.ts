// src/lib/api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Script {
  id: string;
  user_prompt: string;
  script?: string;
  state: ScriptState;
  script_cost?: number;
  video_cost?: number;
  tiktok_url?: string;
  audio_file?: string;
  video_file?: string;
  created_at?: string;
  updated_at?: string;
  active_task_id?: string;
}

export enum ScriptState {
  GENERATING = 1,
  GENERATED = 2,
  PRODUCING = 3,
  PRODUCED = 4,
  UPLOADING = 5,
  UPLOADED = 6,
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async fetch(endpoint: string, options: RequestInit = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(
        `API request failed: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  }

  // Script endpoints
  async getStudioScripts(): Promise<Script[]> {
    return this.fetch("/scripts/studio-scripts");
  }

  async getScript(scriptId: string): Promise<Script> {
    return this.fetch(`/scripts/${scriptId}`);
  }

  async createScript(script: Partial<Script>): Promise<string> {
    return this.fetch("/scripts", {
      method: "POST",
      body: JSON.stringify(script),
    });
  }

  async updateScript(
    scriptId: string,
    updates: Partial<Script>
  ): Promise<void> {
    return this.fetch(`/scripts/${scriptId}`, {
      method: "PUT",
      body: JSON.stringify(updates),
    });
  }

  async deleteScript(scriptId: string): Promise<void> {
    return this.fetch(`/scripts/${scriptId}`, {
      method: "DELETE",
    });
  }

  // Task endpoints
  async generateScript(
    topic: string
  ): Promise<{ task_id: string; topic: string }> {
    return this.fetch("/tasks/generate-script", {
      method: "POST",
      body: JSON.stringify({ topic }),
    });
  }

  async generateVideo(
    scriptId: string,
    script: string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    settings: any = {}
  ): Promise<{ task_id: string }> {
    return this.fetch("/tasks/generate-video", {
      method: "POST",
      body: JSON.stringify({ script_id: scriptId, script, settings }),
    });
  }

  async uploadTikTok(
    scriptId: string,
    videoPath: string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    metadata: any = {}
  ): Promise<{ task_id: string }> {
    return this.fetch("/tasks/upload-tiktok", {
      method: "POST",
      body: JSON.stringify({ script_id: scriptId, video_path: videoPath, metadata }),
    });
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async getTaskStatus(taskId: string): Promise<any> {
    return this.fetch(`/tasks/${taskId}/status`);
  }
}

export const apiClient = new ApiClient();
