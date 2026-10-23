import React from "react";
import { useCurrentFrame } from "remotion";

interface MangaSpeedLinesProps {
  color?: string;
  count?: number;
  innerRadius?: number; // 中央のくり抜き半径（%またはpx）
  opacity?: number;
}

export const MangaSpeedLines: React.FC<MangaSpeedLinesProps> = ({
  color = "#FFE600",
  count = 28,
  innerRadius = 450, // 1080x1920の中央をしっかり開けて犬を見せる
  opacity = 0.85,
}) => {
  const frame = useCurrentFrame();

  // フレームごとに線の角度や太さをジッターさせてコミックのパラパラ感を演出
  const seed = Math.floor(frame / 2); // 2フレームごとに更新してアニメ調に

  const lines = React.useMemo(() => {
    const arr = [];
    const step = 360 / count;
    for (let i = 0; i < count; i++) {
      const pseudoRand = Math.sin((i + 1) * (seed + 13)) * 10000;
      const angle = i * step + ((pseudoRand % 5) - 2.5);
      const width = 2 + Math.abs(pseudoRand % 6);
      const length = 1200 + Math.abs(pseudoRand % 400);
      arr.push({ angle, width, length });
    }
    return arr;
  }, [count, seed]);

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
        opacity,
        // 中央を円形グラデーションマスクでくり抜き、犬を絶対に遮らない
        WebkitMaskImage: `radial-gradient(circle at 50% 48%, transparent 0px, transparent ${innerRadius}px, black ${innerRadius + 180}px)`,
        maskImage: `radial-gradient(circle at 50% 48%, transparent 0px, transparent ${innerRadius}px, black ${innerRadius + 180}px)`,
      }}
    >
      <svg
        width="1080"
        height="1920"
        viewBox="-540 -960 1080 1920"
        style={{ width: "100%", height: "100%" }}
      >
        {lines.map((line, idx) => (
          <line
            key={idx}
            x1="0"
            y1={innerRadius}
            x2="0"
            y2={innerRadius + line.length}
            stroke={color}
            strokeWidth={line.width}
            strokeLinecap="round"
            transform={`rotate(${line.angle})`}
            opacity={0.8 + 0.2 * Math.sin(idx + seed)}
          />
        ))}
      </svg>
    </div>
  );
};
