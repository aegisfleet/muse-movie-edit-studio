import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

interface WaveformVisualizerProps {
  bars: number[];
  rms: number;
  wave: number[];
  primaryColor: string;
  secondaryColor: string;
  accentColor: string;
}

export const WaveformVisualizer: React.FC<WaveformVisualizerProps> = ({
  bars,
  rms,
  wave,
  primaryColor,
  secondaryColor,
  accentColor,
}) => {
  const frame = useCurrentFrame();

  // Width: 880px, Height: 260px
  const width = 880;
  const height = 240;
  const centerY = height / 2;

  // Generate SVG curve from wave points
  const points = (wave && wave.length > 0) ? wave : new Array(48).fill(0);
  const stepX = width / (points.length - 1);

  let pathD = `M 0 ${centerY}`;
  points.forEach((pt, i) => {
    const x = i * stepX;
    // Scale wave amplitude: pt is ~ -0.3 to +0.3
    const y = centerY - pt * (height * 0.9);
    pathD += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
  });

  // Pulse glow scale from RMS
  const pulseScale = 1.0 + rms * 0.25;

  return (
    <div
      style={{
        width: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
      }}
    >
      {/* Background Pulse Glow */}
      <div
        style={{
          position: "absolute",
          width: 500,
          height: 160,
          borderRadius: "50%",
          background: `radial-gradient(ellipse at center, ${primaryColor}40 0%, ${secondaryColor}15 50%, transparent 80%)`,
          transform: `scale(${pulseScale})`,
          filter: "blur(30px)",
          pointerEvents: "none",
          transition: "transform 0.05s ease-out",
        }}
      />

      {/* Visualizer Container (Glass Box) */}
      <div
        style={{
          width,
          height,
          position: "relative",
          borderRadius: 20,
          background: "rgba(15, 20, 32, 0.65)",
          border: `1px solid rgba(255, 255, 255, 0.1)`,
          backdropFilter: "blur(16px)",
          boxShadow: `0 12px 40px rgba(0, 0, 0, 0.5), 0 0 30px ${primaryColor}25`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
        }}
      >
        {/* Subtle Horizontal Center Grid Line */}
        <div
          style={{
            position: "absolute",
            width: "100%",
            height: 1,
            backgroundColor: "rgba(255, 255, 255, 0.08)",
            top: centerY,
          }}
        />

        {/* 1. Mirrored Frequency Equalizer Bars */}
        <div
          style={{
            position: "absolute",
            width: "92%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 10px",
          }}
        >
          {bars.map((b, idx) => {
            // b is 0.02 ~ 1.0
            const barH = Math.max(6, b * (height * 0.78));
            return (
              <div
                key={`bar-${idx}`}
                style={{
                  width: 14,
                  height: barH,
                  borderRadius: 7,
                  background: `linear-gradient(180deg, ${accentColor} 0%, ${primaryColor} 60%, ${secondaryColor} 100%)`,
                  boxShadow: b > 0.15 ? `0 0 10px ${primaryColor}80` : "none",
                  transition: "height 0.04s ease-out",
                }}
              />
            );
          })}
        </div>

        {/* 2. Neon Waveform Oscilloscope Line Overlay */}
        <svg
          width={width}
          height={height}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            pointerEvents: "none",
          }}
        >
          <defs>
            <linearGradient id="waveGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={secondaryColor} stopOpacity="0.4" />
              <stop offset="25%" stopColor={primaryColor} stopOpacity="0.9" />
              <stop offset="50%" stopColor={accentColor} stopOpacity="1.0" />
              <stop offset="75%" stopColor={primaryColor} stopOpacity="0.9" />
              <stop offset="100%" stopColor={secondaryColor} stopOpacity="0.4" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <path
            d={pathD}
            fill="none"
            stroke="url(#waveGrad)"
            strokeWidth="3.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            filter="url(#glow)"
          />
        </svg>

        {/* Bottom Audio Info Badges */}
        <div
          style={{
            position: "absolute",
            bottom: 10,
            right: 18,
            display: "flex",
            gap: 12,
            alignItems: "center",
          }}
        >
          <span
            style={{
              fontSize: 12,
              fontFamily: "monospace",
              color: "rgba(255, 255, 255, 0.45)",
              letterSpacing: 1,
            }}
          >
            48kHz / PCM
          </span>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: rms > 0.03 ? accentColor : "rgba(255, 255, 255, 0.2)",
              boxShadow: rms > 0.03 ? `0 0 8px ${accentColor}` : "none",
            }}
          />
        </div>
      </div>
    </div>
  );
};
