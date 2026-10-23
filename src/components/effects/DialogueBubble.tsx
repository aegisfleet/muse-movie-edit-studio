import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface DialogueBubbleProps {
  speaker: "dog" | "owner";
  name: string;
  avatarEmoji: string;
  text: string;
  startFrame: number;
  durationFrames?: number;
  subText?: string;
  mood?: "panic" | "excited" | "curious" | "tsukkomi" | "smug";
}

export const DialogueBubble: React.FC<DialogueBubbleProps> = ({
  speaker,
  name,
  avatarEmoji,
  text,
  startFrame,
  durationFrames = 80,
  subText,
  mood = "excited",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (frame < startFrame || frame >= startFrame + durationFrames) {
    return null;
  }

  const relFrame = frame - startFrame;

  // Pop in animation
  const pop = spring({
    frame: relFrame,
    fps,
    config: {
      damping: 10,
      mass: 0.5,
      stiffness: 240,
    },
  });

  // Exit fade out
  const exitFrames = 8;
  const remaining = startFrame + durationFrames - frame;
  const exitOpacity = remaining < exitFrames ? remaining / exitFrames : 1.0;

  // Speaker styling
  const isDog = speaker === "dog";
  const alignLeft = isDog;

  // Mood color schemes
  const moodStyles = {
    panic: {
      bg: "linear-gradient(135deg, #FF0844 0%, #FFB199 100%)",
      border: "#FFE600",
      textColor: "#FFFFFF",
      shake: 5,
    },
    excited: {
      bg: "linear-gradient(135deg, #F857A6 0%, #FF5858 100%)",
      border: "#FFFFFF",
      textColor: "#FFFFFF",
      shake: 2,
    },
    curious: {
      bg: "linear-gradient(135deg, #FFA07A 0%, #FF7F50 100%)",
      border: "#FFFFFF",
      textColor: "#FFFFFF",
      shake: 1,
    },
    tsukkomi: {
      bg: "linear-gradient(135deg, #00C6FF 0%, #0072FF 100%)",
      border: "#00F0FF",
      textColor: "#FFFFFF",
      shake: 3,
    },
    smug: {
      bg: "linear-gradient(135deg, #B993D6 0%, #8CA6DB 100%)",
      border: "#FFD700",
      textColor: "#FFFFFF",
      shake: 0,
    },
  }[mood];

  // Subtle continuous jitter for excitement
  const jitterX = moodStyles.shake ? Math.sin(frame * 5) * moodStyles.shake : 0;
  const jitterY = moodStyles.shake ? Math.cos(frame * 4) * (moodStyles.shake * 0.7) : 0;

  return (
    <div
      style={{
        position: "absolute",
        bottom: isDog ? "340px" : "160px",
        left: alignLeft ? "40px" : "auto",
        right: !alignLeft ? "40px" : "auto",
        maxWidth: "880px",
        display: "flex",
        flexDirection: alignLeft ? "row" : "row-reverse",
        alignItems: "flex-end",
        gap: "16px",
        transform: `scale(${pop}) translate(${jitterX}px, ${jitterY}px)`,
        transformOrigin: alignLeft ? "bottom left" : "bottom right",
        opacity: exitOpacity,
        zIndex: 100,
      }}
    >
      {/* Avatar Badge */}
      <div
        style={{
          width: "90px",
          height: "90px",
          borderRadius: "50%",
          background: isDog ? "#FFD93D" : "#4D96FF",
          border: "4px solid #FFFFFF",
          boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          fontSize: "52px",
          flexShrink: 0,
        }}
      >
        {avatarEmoji}
      </div>

      {/* Speech Content Bubble */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: alignLeft ? "flex-start" : "flex-end" }}>
        {/* Speaker Name Tag */}
        <span
          style={{
            fontSize: "24px",
            fontWeight: 900,
            color: "#FFFFFF",
            textShadow: "0 2px 8px rgba(0,0,0,0.8)",
            marginBottom: "6px",
            padding: "2px 14px",
            background: "rgba(0,0,0,0.6)",
            borderRadius: "20px",
          }}
        >
          {name}
        </span>

        {/* Bubble Box */}
        <div
          style={{
            background: moodStyles.bg,
            border: `4px solid ${moodStyles.border}`,
            borderRadius: "24px",
            padding: "16px 28px",
            boxShadow: "0 12px 35px rgba(0,0,0,0.6), 0 0 25px rgba(255,255,255,0.2)",
          }}
        >
          <div
            style={{
              fontSize: "48px",
              fontWeight: 900,
              fontFamily: "'Inter', 'Hiragino Sans', 'Meiryo', sans-serif",
              color: moodStyles.textColor,
              WebkitTextStroke: "2px rgba(0,0,0,0.4)",
              textShadow: "0 4px 12px rgba(0,0,0,0.7)",
              lineHeight: 1.25,
              whiteSpace: "pre-line",
            }}
          >
            {text}
          </div>

          {subText && (
            <div
              style={{
                fontSize: "28px",
                fontWeight: 800,
                color: "#FFE600",
                marginTop: "6px",
                textShadow: "0 2px 6px rgba(0,0,0,0.8)",
              }}
            >
              {subText}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
