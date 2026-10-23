import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface BadgeTextProps {
  text: string;
  startFrame?: number;
  bgColor?: string;
  textColor?: string;
  fontSize?: number;
  rotation?: number;
}

export const BadgeText: React.FC<BadgeTextProps> = ({
  text,
  startFrame = 0,
  bgColor = "#FF3366",
  textColor = "#FFFFFF",
  fontSize = 48,
  rotation = -2,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - startFrame);

  const scale = spring({
    frame: relFrame,
    fps,
    config: {
      damping: 10,
      mass: 0.6,
      stiffness: 220,
    },
  });

  if (frame < startFrame) return null;

  return (
    <div
      style={{
        display: "inline-block",
        transform: `scale(${scale}) rotate(${rotation}deg)`,
        transformOrigin: "center center",
      }}
    >
      <div
        style={{
          background: bgColor,
          color: textColor,
          fontSize: `${fontSize}px`,
          fontWeight: 900,
          fontFamily: "'Inter', 'Hiragino Sans', 'Meiryo', sans-serif",
          padding: "10px 28px",
          borderRadius: "16px",
          boxShadow: "0 12px 30px rgba(0,0,0,0.5), 0 0 20px rgba(255,255,255,0.2)",
          letterSpacing: "2px",
          border: "3px solid #FFFFFF",
          textShadow: "0 2px 4px rgba(0,0,0,0.4)",
        }}
      >
        {text}
      </div>
    </div>
  );
};
