import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TextSparkDeco } from "./TextSparkDeco";

export interface JizuraFloatingTextProps {
  text: string;
  startFrame: number;
  endFrame: number;
  fontSize?: number;
  textColor?: string;
  strokeColor?: string;
  strokeWidth?: number;
  glowColor?: string;
  subGlowColor?: string;
  delayPerChar?: number;
  position?: "bottom" | "center" | "top";
  yOffset?: number;
  floatIntensity?: number;
  withSparks?: boolean;
  sparkColor?: string;
}

export const JizuraFloatingText: React.FC<JizuraFloatingTextProps> = ({
  text,
  startFrame,
  endFrame,
  fontSize = 68,
  textColor = "#FFFFFF",
  strokeColor = "#111111",
  strokeWidth = 6,
  glowColor = "rgba(255, 107, 139, 0.85)",
  subGlowColor = "rgba(255, 230, 0, 0.6)",
  delayPerChar = 1.2,
  position = "bottom",
  yOffset = 0,
  floatIntensity = 1.0,
  withSparks = true,
  sparkColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (frame < startFrame || frame > endFrame) {
    return null;
  }

  const duration = endFrame - startFrame;
  const currentRelFrame = frame - startFrame;

  // 最後の14フレームで「上へ浮かび上がりながら解けて消える」
  const outStartFrame = duration - 14;
  const isExiting = currentRelFrame >= outStartFrame;
  const exitProgress = isExiting
    ? (currentRelFrame - outStartFrame) / 14
    : 0;

  const exitTranslateY = -exitProgress * 55; // 上へふわっと昇る
  const exitScale = 1.0 + exitProgress * 0.12; // わずかに広がる
  const exitOpacity = Math.max(0, 1.0 - exitProgress);
  const exitLetterSpacing = exitProgress * 8; // 文字間がフワッと解ける

  // アイドル時の微細な浮遊（サイン波）
  const idleFloatY = Math.sin(frame * 0.1) * 6 * floatIntensity;
  const idleRotate = Math.sin(frame * 0.08) * 1.8 * floatIntensity;

  const chars = Array.from(text);

  // 文字数に応じた自動リサイズ（1行に美しく収める）
  let actualFontSize = fontSize;
  if (chars.length >= 18) {
    actualFontSize = Math.min(fontSize, 50);
  } else if (chars.length >= 14) {
    actualFontSize = Math.min(fontSize, 58);
  } else if (chars.length >= 11) {
    actualFontSize = Math.min(fontSize, 66);
  }

  let baseTop = "1320px";
  if (position === "top") baseTop = "320px";
  if (position === "center") baseTop = "880px";

  return (
    <div
      style={{
        position: "absolute",
        top: baseTop,
        left: 0,
        width: "1080px",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        pointerEvents: "none",
        transform: `translateY(${yOffset + exitTranslateY + idleFloatY}px) scale(${exitScale}) rotate(${idleRotate}deg)`,
        opacity: exitOpacity,
        letterSpacing: `${exitLetterSpacing}px`,
        transformOrigin: "center center",
      }}
    >
      {/* 文字の背後に直接重なるスパーク演出 */}
      {withSparks && (
        <div style={{ position: "absolute", left: "50%", top: "50%" }}>
          <TextSparkDeco
            startFrame={startFrame + 2}
            color={sparkColor || glowColor}
            width={Math.min(900, chars.length * actualFontSize * 0.95 + 160)}
            height={actualFontSize * 1.8}
          />
        </div>
      )}

      <div
        style={{
          display: "inline-flex",
          whiteSpace: "nowrap",
          justifyContent: "center",
          alignItems: "center",
          padding: "10px 20px",
          gap: "1px",
        }}
      >
        {chars.map((char, index) => {
          const charStart = index * delayPerChar;
          const charRelFrame = currentRelFrame - charStart;

          // 各文字のバウンス出現 spring
          const spr = spring({
            frame: Math.max(0, charRelFrame),
            fps,
            config: {
              damping: 10,
              mass: 0.45,
              stiffness: 220,
            },
          });

          const charTranslateY = (1 - spr) * 55;
          const charScale = charRelFrame < 0 ? 0 : spr;
          const charRotate = (1 - spr) * (index % 2 === 0 ? -12 : 12);
          const charOpacity = Math.min(1, Math.max(0, charRelFrame / 3));

          return (
            <span
              key={index}
              style={{
                display: "inline-block",
                fontSize: `${actualFontSize}px`,
                fontWeight: 900,
                fontFamily: "'Inter', 'Hiragino Sans', 'Meiryo', sans-serif",
                color: textColor,
                WebkitTextStroke: `${strokeWidth}px ${strokeColor}`,
                paintOrder: "stroke fill",
                textShadow: `
                  0 0 16px ${glowColor},
                  0 0 32px ${subGlowColor},
                  0 6px 0 ${strokeColor},
                  0 12px 24px rgba(0, 0, 0, 0.9)
                `,
                transform: `translateY(${charTranslateY}px) scale(${charScale}) rotate(${charRotate}deg)`,
                opacity: charOpacity,
                transformOrigin: "bottom center",
              }}
            >
              {char}
            </span>
          );
        })}
      </div>
    </div>
  );
};
