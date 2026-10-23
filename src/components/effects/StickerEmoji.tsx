import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface StickerEmojiProps {
  emoji: string;
  startFrame?: number;
  size?: number;
  rotation?: number;
  x?: number;
  y?: number;
}

export const StickerEmoji: React.FC<StickerEmojiProps> = ({
  emoji,
  startFrame = 0,
  size = 100,
  rotation = 12,
  x = 0,
  y = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - startFrame);

  const scale = spring({
    frame: relFrame,
    fps,
    config: {
      damping: 9,
      mass: 0.5,
      stiffness: 260,
    },
  });

  // Continuous subtle floating
  const floatY = Math.sin((frame - startFrame) * 0.1) * 8;

  if (frame < startFrame) return null;

  return (
    <div
      style={{
        position: "absolute",
        left: `${x}px`,
        top: `${y}px`,
        fontSize: `${size}px`,
        transform: `scale(${scale}) rotate(${rotation}deg) translateY(${floatY}px)`,
        transformOrigin: "center center",
        filter: "drop-shadow(0 10px 20px rgba(0,0,0,0.6))",
        pointerEvents: "none",
        zIndex: 50,
      }}
    >
      {emoji}
    </div>
  );
};
