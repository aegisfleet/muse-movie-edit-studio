import React from "react";
import { useCurrentFrame, spring } from "remotion";

interface TextSparkDecoProps {
  startFrame: number;
  color?: string;
  width?: number;
  height?: number;
}

export const TextSparkDeco: React.FC<TextSparkDecoProps> = ({
  startFrame,
  color = "#FFD93D",
  width = 600,
  height = 140,
}) => {
  const frame = useCurrentFrame();
  const progress = frame - startFrame;

  if (progress < 0 || progress > 45) return null;

  const scale = spring({
    frame: progress,
    fps: 30,
    config: { damping: 12, stiffness: 220 },
  });

  const fadeOut = progress > 25 ? Math.max(0, 1 - (progress - 25) / 20) : 1;

  return (
    <div
      style={{
        position: "absolute",
        left: "50%",
        top: "50%",
        transform: `translate(-50%, -50%) scale(${scale})`,
        width: `${width}px`,
        height: `${height}px`,
        pointerEvents: "none",
        opacity: fadeOut,
      }}
    >
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 600 140"
        style={{ overflow: "visible" }}
      >
        {/* 左側の飛び散るスパークライン */}
        <line
          x1="30"
          y1="70"
          x2="-40"
          y2="30"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
        />
        <line
          x1="20"
          y1="90"
          x2="-50"
          y2="105"
          stroke={color}
          strokeWidth="5"
          strokeLinecap="round"
        />
        <line
          x1="45"
          y1="35"
          x2="-20"
          y2="-15"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
        />

        {/* 右側の飛び散るスパークライン */}
        <line
          x1="570"
          y1="70"
          x2="640"
          y2="30"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
        />
        <line
          x1="580"
          y1="90"
          x2="650"
          y2="105"
          stroke={color}
          strokeWidth="5"
          strokeLinecap="round"
        />
        <line
          x1="555"
          y1="35"
          x2="620"
          y2="-15"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
        />

        {/* 周囲の小さなキラリ星・ドット */}
        <circle cx="-25" cy="55" r="5" fill="#FFF" />
        <circle cx="625" cy="55" r="5" fill="#FFF" />
        <circle cx="70" cy="-20" r="4" fill={color} />
        <circle cx="530" cy="-20" r="4" fill={color} />
      </svg>
    </div>
  );
};
