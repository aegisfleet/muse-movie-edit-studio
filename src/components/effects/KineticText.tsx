import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface KineticTextProps {
  text: string;
  startFrame?: number;
  fontSize?: number;
  color?: string;
  strokeColor?: string;
  glowColor?: string;
  delayPerChar?: number;
  className?: string;
}

export const KineticText: React.FC<KineticTextProps> = ({
  text,
  startFrame = 0,
  fontSize = 64,
  color = "#FFFFFF",
  strokeColor = "#111111",
  glowColor = "rgba(255, 215, 0, 0.6)",
  delayPerChar = 2,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const chars = Array.from(text);

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        alignItems: "center",
        gap: "4px",
      }}
    >
      {chars.map((char, index) => {
        const charStart = startFrame + index * delayPerChar;
        const relativeFrame = frame - charStart;

        // spring for scale and bounce
        const spr = spring({
          frame: Math.max(0, relativeFrame),
          fps,
          config: {
            damping: 12,
            mass: 0.5,
            stiffness: 180,
          },
        });

        // Rotation & translation
        const translateY = (1 - spr) * 80;
        const scale = relativeFrame < 0 ? 0 : spr;
        const rotate = (1 - spr) * (index % 2 === 0 ? -15 : 15);
        const opacity = Math.min(1, Math.max(0, relativeFrame / 3));

        return (
          <span
            key={index}
            style={{
              display: "inline-block",
              fontSize: `${fontSize}px`,
              fontWeight: 900,
              fontFamily: "'Inter', 'Hiragino Sans', 'Meiryo', sans-serif",
              color,
              WebkitTextStroke: `4px ${strokeColor}`,
              paintOrder: "stroke fill",
              textShadow: `0 8px 24px ${glowColor}, 0 2px 4px rgba(0,0,0,0.8)`,
              transform: `translateY(${translateY}px) scale(${scale}) rotate(${rotate}deg)`,
              opacity,
              transformOrigin: "bottom center",
            }}
          >
            {char}
          </span>
        );
      })}
    </div>
  );
};
