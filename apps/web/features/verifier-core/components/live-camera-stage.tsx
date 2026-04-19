"use client";

import type { RefObject } from "react";

export function LiveCameraStage(props: {
  videoRef: RefObject<HTMLVideoElement | null>;
  overlayCanvasRef: RefObject<HTMLCanvasElement | null>;
  captureCanvasRef: RefObject<HTMLCanvasElement | null>;
  status: string;
  detail: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-none border border-line bg-panel shadow-panel">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(0,85,255,0.12),transparent_48%)]" />
      <div className="scanlines pointer-events-none absolute inset-0 opacity-30" />
      <div className="relative p-4 sm:p-6">
        <div className="mb-4 flex items-center justify-between gap-4 border-b border-line/70 pb-3">
          <div>
            <p className="text-[0.65rem] uppercase tracking-[0.3em] text-muted-foreground">
              Live Capture
            </p>
            <h2 className="font-headline text-2xl uppercase tracking-tight text-foreground sm:text-3xl">
              Identity Canvas
            </h2>
          </div>
          <div className="text-right text-[0.68rem] uppercase tracking-[0.22em] text-muted-foreground">
            <div>{props.status}</div>
            <div className="mt-1 text-signal-cyan">{props.detail}</div>
          </div>
        </div>

        <div className="relative aspect-[4/5] min-h-[24rem] overflow-hidden border border-line/70 bg-black sm:aspect-[4/3]">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(0,212,255,0.18),transparent_58%)]" />
          <div className="video-shell absolute inset-0">
            <video ref={props.videoRef} className="video h-full min-h-0 border-0" playsInline muted />
            <canvas ref={props.overlayCanvasRef} className="overlay-canvas" />
          </div>
          <div className="pointer-events-none absolute inset-6 border border-accent/60" />
          <div className="pointer-events-none absolute bottom-4 left-4 bg-background/80 px-3 py-2 text-[0.62rem] uppercase tracking-[0.28em] text-accent backdrop-blur">
            Frame aligned
          </div>
          <div className="pointer-events-none absolute right-4 top-4 h-2 w-2 rounded-full bg-accent shadow-[0_0_18px_rgba(0,85,255,0.7)]" />
        </div>

        <canvas ref={props.captureCanvasRef} className="hidden-canvas" />
      </div>
    </div>
  );
}
