"use client";

import { useCallback, useEffect, useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import VideoCard from "@/components/VideoCard";
import {
  checkHealth,
  ingestVideos,
  type VideoMetadata,
} from "@/lib/api";

export default function Home() {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [instagramUrl, setInstagramUrl] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [videos, setVideos] = useState<VideoMetadata[]>([]);
  const [ingesting, setIngesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  useEffect(() => {
    checkHealth().then(setBackendOk);
  }, []);

  const onIngest = useCallback(async () => {
    setError(null);
    setIngesting(true);
    setSessionId(null);
    setVideos([]);
    try {
      const res = await ingestVideos(youtubeUrl.trim(), instagramUrl.trim());
      setSessionId(res.session_id);
      setVideos(res.videos);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ingest failed");
    } finally {
      setIngesting(false);
    }
  }, [youtubeUrl, instagramUrl]);

  const videoA = videos.find((v) => v.video_id === "A");
  const videoB = videos.find((v) => v.video_id === "B");

  return (
    <div className="app-shell">
      <header className="header">
        <h1>Creator Video RAG</h1>
        <span className="status">
          Backend:{" "}
          {backendOk === null ? "…" : backendOk ? "connected" : "offline"} · LangChain
          + Chroma
        </span>
      </header>

      <div className="main-grid">
        <section className="panel">
          <form
            className="ingest-form"
            onSubmit={(e) => {
              e.preventDefault();
              onIngest();
            }}
          >
            <label htmlFor="yt">Video A — YouTube URL</label>
            <input
              id="yt"
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              required
            />
            <label htmlFor="ig">Video B — Instagram Reel URL</label>
            <input
              id="ig"
              value={instagramUrl}
              onChange={(e) => setInstagramUrl(e.target.value)}
              placeholder="https://www.instagram.com/reel/..."
              required
            />
            {error && <div className="error-banner">{error}</div>}
            <button
              type="submit"
              className="btn btn-primary"
              disabled={ingesting}
            >
              {ingesting ? (
                <>
                  <span className="loader" />
                  Fetching transcripts & embedding…
                </>
              ) : (
                "Ingest & build index"
              )}
            </button>
          </form>

          {videoA ? (
            <VideoCard video={videoA} />
          ) : (
            <p className="empty-state">YouTube card appears after ingest</p>
          )}
        </section>

        <section className="panel">
          {videoB ? (
            <VideoCard video={videoB} />
          ) : (
            <p className="empty-state" style={{ marginTop: "7rem" }}>
              Instagram card appears after ingest
            </p>
          )}
          {sessionId && (
            <p
              style={{
                marginTop: "1rem",
                fontSize: "0.72rem",
                color: "var(--muted)",
                wordBreak: "break-all",
              }}
            >
              Session: {sessionId}
            </p>
          )}
        </section>

        <section className="panel chat-panel">
          <ChatPanel sessionId={sessionId} disabled={ingesting} />
        </section>
      </div>
    </div>
  );
}
