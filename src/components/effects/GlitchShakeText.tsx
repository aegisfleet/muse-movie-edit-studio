import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface GlitchShakeTextProps {
  text: string;
  startFrame?: number;
  fontSize?: number;
  color?: string;
  intensity?: number;
}

export const GlitchShakeText: React.FC<GlitchShakeTextProps> = ({
  text,
  startFrame = 0,
  fontSize = 72,
  color = "#FFE600",
  intensity = 6,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - startFrame);

  // Initial impact pop
  const pop = spring({
    frame: relFrame,
    fps,
    config: {
      damping: 8,
      mass: 0.4,
      stiffness: 250,
    },
  });

  // Jitter calculation
  const shakeX = (Math.sin(frame * 4.7) * intensity * (1 - Math.min(1, relFrame / 30))) || 0;
  const shakeY = (Math.cos(frame * 3.3) * intensity * (1 - Math.min(1, relFrame / 30))) || 0;

  if (frame < startFrame) return null;

  return (
    <div
      style={{
        position: "relative",
        display: "inline-block",
        transform: `scale(${pop}) translate(${shakeX}px, ${shakeY}px)`,
        transformOrigin: "center center",
      }}
    >
      {/* Chromatic aberration layers */}
      <span
        style={{
          position: "absolute",
          left: "-4px",
          top: "0",
          fontSize: `${fontSize}px`,
          fontWeight: 900,
          fontFamily: "'Inter', 'Hiragino Sans', 'Meiryo', sans-serif",
          color: "#00F0FF",
          opacity: 0.7,
          mixBlendMode: "screen",
          WebkitTextStroke: "2px #00F0FF",
        }}
      >
        {text}
      </span>
      <span
        style={{
          position: "absolute",
          left: "4px",
          top: "0",
          fontSize: `${fontSize}px`,
          fontWeight: 900,
          fontFamily: "'Inter', 'Hiragino Sans', 'Meiryo', sans-serif",
          color: "#FF0055",
          opacity: 0.7,
          mixBlendMode: "screen",
          WebkitTextStroke: "2px #FF0055",
        }}
      >
        {text}
      </span>

      {/* Main Text */}
      <span
        style={{
          position: "relative",
          fontSize: `${fontSize}px`,
          fontWeight: 900,
          fontFamily: "'Inter', 'Hiragino Sans', 'Meiryo', sans-serif",
          color,
          WebkitTextStroke: "5px #111111",
          paintOrder: "stroke fill",
          textShadow: "0 10px 30px rgba(0,0,0,0.8), 0 0 20px rgba(255,230,0,0.8)",
        }}
      >
        {text}
      </span>
    </div>
  );
};
