const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type VideoId = "A" | "B";

export interface TranscriptSegment {
  start: number;
  text: string;
}

export interface VideoMetadata {
  video_id: VideoId;
  platform: "youtube" | "instagram";
  source_url: string;
  title?: string | null;
  creator?: string | null;
  follower_count?: number | null;
  views?: number | null;
  likes?: number | null;
  comments?: number | null;
  engagement_rate?: number | null;
  hashtags: string[];
  upload_date?: string | null;
  duration_seconds?: number | null;
  thumbnail_url?: string | null;
  transcript: TranscriptSegment[];
  transcript_text: string;
}

export interface IngestResponse {
  session_id: string;
  videos: VideoMetadata[];
  chunk_count: number;
  message: string;
}

export interface SourceCitation {
  video_id: VideoId;
  chunk_index: number;
  platform: string;
  excerpt: string;
  source_url?: string | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  streaming?: boolean;
}

export async function ingestVideos(
  youtubeUrl: string,
  instagramUrl: string
): Promise<IngestResponse> {
  const res = await fetch(`${API_BASE}/api/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      youtube_url: youtubeUrl,
      instagram_url: instagramUrl,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).join(", ")
          : `Ingest failed (${res.status})`;
    throw new Error(msg);
  }
  return res.json();
}

export async function streamChat(
  sessionId: string,
  message: string,
  onToken: (token: string) => void,
  onSources: (sources: SourceCitation[]) => void,
  onDone: (fullAnswer: string) => void,
  onError: (msg: string) => void
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });

  if (!res.ok || !res.body) {
    onError(`Chat request failed (${res.status})`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const lines = part.split("\n");
      let event = "message";
      let data = "";
      for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        if (line.startsWith("data:")) data = line.slice(5).trim();
      }
      if (!data) continue;
      try {
        const parsed = JSON.parse(data);
        if (event === "token") onToken(parsed.content ?? "");
        else if (event === "sources") onSources(parsed.sources ?? []);
        else if (event === "done") onDone(parsed.answer ?? "");
        else if (event === "error") onError(parsed.message ?? "Unknown error");
      } catch {
        /* skip malformed */
      }
    }
  }
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    const data = await res.json();
    return data.status === "ok";
  } catch {
    return false;
  }
}
