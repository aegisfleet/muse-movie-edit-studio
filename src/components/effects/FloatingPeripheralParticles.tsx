import React from "react";
import { useCurrentFrame } from "remotion";

interface FloatingPeripheralParticlesProps {
  type: "tears" | "sparks" | "petals" | "hearts" | "curious";
  count?: number;
  opacity?: number;
}

export const FloatingPeripheralParticles: React.FC<FloatingPeripheralParticlesProps> = ({
  type,
  count = 12,
  opacity = 0.85,
}) => {
  const frame = useCurrentFrame();

  const particles = React.useMemo(() => {
    const list = [];
    for (let i = 0; i < count; i++) {
      // 画面の左右外周（犬のいないエリア）に配置
      const isLeft = i % 2 === 0;
      const baseX = isLeft ? 50 + (i * 17) % 110 : 920 + (i * 23) % 110;
      const baseY = 250 + (i * 135) % 1300;
      const speed = 1.2 + (i % 3) * 0.6;
      const size = 24 + (i % 4) * 8;
      const delay = (i * 7) % 60;
      list.push({ baseX, baseY, speed, size, delay, id: i });
    }
    return list;
  }, [count]);

  const getEmoji = (t: string, id: number) => {
    switch (t) {
      case "tears":
        return id % 2 === 0 ? "💧" : "🥺";
      case "sparks":
        return id % 3 === 0 ? "✨" : id % 3 === 1 ? "⭐" : "🌟";
      case "petals":
        return id % 2 === 0 ? "🌸" : "🐾";
      case "hearts":
        return id % 3 === 0 ? "💖" : id % 3 === 1 ? "💕" : "✨";
      case "curious":
        return id % 2 === 0 ? "🔍" : "❓";
      default:
        return "✨";
    }
  };

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
      }}
    >
      {particles.map((p) => {
        // 上昇または下降アニメーション
        const activeFrame = frame + p.delay;
        const yOffset =
          type === "tears"
            ? (activeFrame * p.speed * 2.5) % 1400 // 涙は下に落ちる
            : -((activeFrame * p.speed * 2.2) % 1400); // その他は上にフワフワ浮く
        const currentY = (p.baseY + yOffset + 1400) % 1400 + 200;
        const waveX = Math.sin(activeFrame * 0.05 + p.id) * 20;
        const rot = Math.sin(activeFrame * 0.04 + p.id) * 25;
        const fade =
          Math.sin(((currentY - 200) / 1400) * Math.PI) * 0.85 + 0.15;

        return (
          <div
            key={p.id}
            style={{
              position: "absolute",
              left: `${p.baseX + waveX}px`,
              top: `${currentY}px`,
              fontSize: `${p.size}px`,
              transform: `rotate(${rot}deg)`,
              opacity: Math.max(0, fade),
              filter: "drop-shadow(0 4px 10px rgba(0,0,0,0.4))",
            }}
          >
            {getEmoji(type, p.id)}
          </div>
        );
      })}
    </div>
  );
};
