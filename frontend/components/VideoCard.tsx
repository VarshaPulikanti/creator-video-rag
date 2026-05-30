"use client";

import type { VideoMetadata } from "@/lib/api";

function fmt(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function fmtDate(raw: string | number | null | undefined): string {
  if (raw == null || raw === "") return "—";
  if (typeof raw === "number") {
    const d = new Date(raw > 1e12 ? raw : raw * 1000);
    return d.toISOString().slice(0, 10);
  }
  if (/^\d{8}$/.test(String(raw))) {
    const s = String(raw);
    const y = s.slice(0, 4);
    const m = s.slice(4, 6);
    const d = s.slice(6, 8);
    return `${y}-${m}-${d}`;
  }
  return String(raw);
}

function fmtDuration(sec: number | null | undefined): string {
  if (sec == null) return "—";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

interface Props {
  video: VideoMetadata;
}

export default function VideoCard({ video }: Props) {
  const isA = video.video_id === "A";
  const label = isA ? "Video A · YouTube" : "Video B · Instagram";

  return (
    <article className={`video-card tag-${video.video_id.toLowerCase()}`}>
      {video.thumbnail_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          className="thumb"
          src={video.thumbnail_url}
          alt={video.title ?? label}
          loading="lazy"
        />
      ) : (
        <div className="thumb" />
      )}
      <div className="body">
        <span className={`badge badge-${video.video_id.toLowerCase()}`}>{label}</span>
        <h2>{video.title ?? "Untitled"}</h2>
        <p style={{ fontSize: "0.8rem", color: "var(--muted)" }}>
          {video.creator ?? "Unknown creator"}
          {video.follower_count != null && (
            <> · {fmt(video.follower_count)} followers</>
          )}
        </p>

        <p className="engagement">
          Engagement: {video.engagement_rate != null ? `${video.engagement_rate}%` : "N/A"}
        </p>

        <div className="stats-grid">
          <div className="stat">
            <label>Views</label>
            <span className="value">{fmt(video.views)}</span>
          </div>
          <div className="stat">
            <label>Likes</label>
            <span className="value">{fmt(video.likes)}</span>
          </div>
          <div className="stat">
            <label>Comments</label>
            <span className="value">{fmt(video.comments)}</span>
          </div>
          <div className="stat">
            <label>Duration</label>
            <span className="value">{fmtDuration(video.duration_seconds)}</span>
          </div>
          <div className="stat">
            <label>Uploaded</label>
            <span className="value">{fmtDate(video.upload_date)}</span>
          </div>
          <div className="stat">
            <label>Transcript</label>
            <span className="value">
              {video.transcript.length > 0
                ? `${video.transcript.length} segments`
                : "caption only"}
            </span>
          </div>
        </div>

        {video.hashtags.length > 0 && (
          <div className="hashtags">
            {video.hashtags.slice(0, 12).map((tag) => (
              <span key={tag}>{tag.startsWith("#") ? tag : `#${tag}`}</span>
            ))}
          </div>
        )}

        <p style={{ marginTop: "0.6rem", fontSize: "0.75rem" }}>
          <a href={video.source_url} target="_blank" rel="noreferrer">
            Open source ↗
          </a>
        </p>
      </div>
    </article>
  );
}
