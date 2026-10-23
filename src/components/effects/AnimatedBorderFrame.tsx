import React from "react";
import { useCurrentFrame } from "remotion";

interface AnimatedBorderFrameProps {
  color?: string;
  accentColor?: string;
  theme?: "cute" | "action" | "curious" | "chill";
}

export const AnimatedBorderFrame: React.FC<AnimatedBorderFrameProps> = ({
  color = "rgba(255, 255, 255, 0.4)",
  accentColor = "#FF6B8B",
  theme = "cute",
}) => {
  const frame = useCurrentFrame();

  // 微細な脈動アニメーション
  const pulse = Math.sin(frame * 0.08) * 0.15 + 0.85;
  const dashOffset = (frame * 3) % 40;

  const inset = 36;
  const cornerSize = 48;
  const cornerThickness = 4;

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "1080px",
        height: "1920px",
        pointerEvents: "none",
        overflow: "hidden",
      }}
    >
      {/* 画面外周のソフトなビネット・カラーグロー */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          boxShadow: `inset 0 0 60px ${accentColor}33, inset 0 0 120px rgba(0,0,0,0.4)`,
        }}
      />

      {/* 外周フレーム枠線 */}
      <svg
        width="1080"
        height="1920"
        style={{ position: "absolute", top: 0, left: 0 }}
      >
        <rect
          x={inset}
          y={inset}
          width={1080 - inset * 2}
          height={1920 - inset * 2}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeDasharray={theme === "action" ? "12, 8" : "none"}
          strokeDashoffset={theme === "action" ? -dashOffset : 0}
          rx="24"
          ry="24"
          opacity={pulse}
        />

        {/* 四隅のコーナーデコレーション（L字アクセント） */}
        {/* Top-Left */}
        <path
          d={`M ${inset} ${inset + cornerSize} L ${inset} ${inset} L ${inset + cornerSize} ${inset}`}
          fill="none"
          stroke={accentColor}
          strokeWidth={cornerThickness}
          strokeLinecap="round"
        />
        {/* Top-Right */}
        <path
          d={`M ${1080 - inset - cornerSize} ${inset} L ${1080 - inset} ${inset} L ${1080 - inset} ${inset + cornerSize}`}
          fill="none"
          stroke={accentColor}
          strokeWidth={cornerThickness}
          strokeLinecap="round"
        />
        {/* Bottom-Left */}
        <path
          d={`M ${inset} ${1920 - inset - cornerSize} L ${inset} ${1920 - inset} L ${inset + cornerSize} ${1920 - inset}`}
          fill="none"
          stroke={accentColor}
          strokeWidth={cornerThickness}
          strokeLinecap="round"
        />
        {/* Bottom-Right */}
        <path
          d={`M ${1080 - inset - cornerSize} ${1920 - inset} L ${1080 - inset} ${1920 - inset} L ${1080 - inset} ${1920 - inset - cornerSize}`}
          fill="none"
          stroke={accentColor}
          strokeWidth={cornerThickness}
          strokeLinecap="round"
        />

        {/* コーナーのドットアクセント */}
        <circle cx={inset + 14} cy={inset + 14} r="3" fill={accentColor} />
        <circle cx={1080 - inset - 14} cy={inset + 14} r="3" fill={accentColor} />
        <circle cx={inset + 14} cy={1920 - inset - 14} r="3" fill={accentColor} />
        <circle cx={1080 - inset - 14} cy={1920 - inset - 14} r="3" fill={accentColor} />
      </svg>
    </div>
  );
};
