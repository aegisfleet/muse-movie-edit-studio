import React from "react";
import { useCurrentFrame } from "remotion";
import { JizuraFloatingText } from "./effects/JizuraFloatingText";
import { StickerEmoji } from "./effects/StickerEmoji";
import { AnimatedBorderFrame } from "./effects/AnimatedBorderFrame";
import { MangaSpeedLines } from "./effects/MangaSpeedLines";
import { FloatingPeripheralParticles } from "./effects/FloatingPeripheralParticles";
import projectConfig from "../../public/project_config.json";

export const TimelineOverlay: React.FC = () => {
  const frame = useCurrentFrame();
  const theme = projectConfig.theme as any;
  // scenes は YAML 由来で stickers など任意項目を含むため any として扱う
  const scenes = projectConfig.scenes as any[];

  // 現在フレームのアクティブなシーンを取得
  const currentScene = scenes.find(
    (sc) => frame >= sc.start_frame && frame < sc.end_frame
  );

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
      {/* ========================================================
          1. 動的ボーダーフレーム（画面外周装飾・主役の被写体を保護）
         ======================================================== */}
      {currentScene && currentScene.border_theme !== "none" && (theme as any)?.show_border !== false && (
        <AnimatedBorderFrame
          accentColor={currentScene.border_color ?? "#FF6B8B"}
          theme={(currentScene.border_theme as any) ?? "cute"}
        />
      )}

      {/* ========================================================
          2. トップチャンネルバナー / バッジ
         ======================================================== */}
      {!(theme as any)?.hide_banner && theme?.channel_name && (
        <div
          style={{
            position: "absolute",
            top: "80px",
            left: "60px",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            background: "rgba(0,0,0,0.68)",
            backdropFilter: "blur(14px)",
            padding: "12px 28px",
            borderRadius: "100px",
            border: "2px solid rgba(255,255,255,0.35)",
            boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
          }}
        >
          {theme?.channel_badge && (
            <span style={{ fontSize: "32px" }}>
              {theme.channel_badge}
            </span>
          )}
          <span
            style={{
              color: "#FFF",
              fontSize: "26px",
              fontWeight: 900,
              letterSpacing: "1.5px",
              fontFamily: "'Inter', sans-serif",
            }}
          >
            {theme.channel_name}
          </span>
        </div>
      )}

      {/* ========================================================
          3. シーン別パーティクル & 集中線演出
         ======================================================== */}
      {currentScene && (
        <>
          {currentScene.speed_lines && (
            <MangaSpeedLines
              color={currentScene.border_color ?? "#FFE600"}
              innerRadius={460}
              count={32}
              opacity={0.8}
            />
          )}
          {currentScene.particle_type && (
            <FloatingPeripheralParticles
              type={currentScene.particle_type as any}
              count={10}
              opacity={0.85}
            />
          )}
        </>
      )}

      {/* ========================================================
          4. JIZURA風フローティングテキスト（動的データ駆動）
         ======================================================== */}
      {scenes.flatMap((sc: any, scIdx: number) =>
        (sc.subtitles ?? []).map((sub: any, subIdx: number) => {
          const start = sc.start_frame + sub.start_offset;
          const end = start + sub.duration;
          return (
            <JizuraFloatingText
              key={`sub-${scIdx}-${subIdx}`}
              text={sub.text}
              startFrame={start}
              endFrame={end}
              fontSize={sub.font_size ?? 72}
              textColor={sub.text_color ?? "#FFFFFF"}
              glowColor={sub.glow_color ?? "rgba(255, 107, 139, 0.95)"}
              subGlowColor={(sub as any).sub_glow_color ?? "rgba(255, 230, 0, 0.7)"}
              sparkColor={sub.spark_color ?? "#FF6B8B"}
              floatIntensity={(sub as any).float_intensity ?? 1.5}
              yOffset={sub.y_offset ?? -40}
            />
          );
        })
      )}

      {/* ========================================================
          5. アニメーション絵文字ステッカー（動的データ駆動・シーン限定）
         ======================================================== */}
      {currentScene &&
        (currentScene.stickers ?? []).map((st: any, stIdx: number) => {
          const start = currentScene.start_frame + st.start_offset;
          return (
            <StickerEmoji
              key={`stk-${currentScene.id}-${stIdx}`}
              emoji={st.emoji}
              startFrame={start}
              size={st.size ?? 130}
              rotation={st.rotation ?? 0}
              x={st.x ?? 840}
              y={st.y ?? 460}
            />
          );
        })}
    </div>
  );
};
