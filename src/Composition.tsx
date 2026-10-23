import {
  AbsoluteFill,
  OffthreadVideo,
  Audio,
  Sequence,
  staticFile,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { TimelineOverlay } from "./components/TimelineOverlay";
import projectConfig from "../public/project_config.json";

export const ShortVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const theme = projectConfig.theme as any;
  // scenes は YAML 由来で narration / se など任意項目を含むため any として扱う
  const scenes = projectConfig.scenes as any[];

  // 最後の約1.2秒（35フレーム）でシネマティックにフェードアウト
  const totalFrames = projectConfig.total_frames ?? 900;
  const fadeOutFrames = 35;
  const videoFadeOpacity = interpolate(
    frame,
    [totalFrames - fadeOutFrames, totalFrames - 1],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const audioFade = interpolate(
    frame,
    [totalFrames - fadeOutFrames, totalFrames - 1],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      {/* ========================================================
          1. GoPro Background Video (HLG->Rec.709 & Color Graded)
         ======================================================== */}
      <OffthreadVideo
        src={staticFile("background_30s.mp4")}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />

      {/* ========================================================
          2. Vignette Gradient Overlay (テロップ視認性向上)
         ======================================================== */}
      <AbsoluteFill
        style={{
          pointerEvents: "none",
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 18%, rgba(0,0,0,0) 65%, rgba(0,0,0,0.8) 100%)",
        }}
      />

      {/* ========================================================
          3. JIZURA-style Dynamic Overlay (Subtitles, Borders, SE)
         ======================================================== */}
      <TimelineOverlay />

      {/* ========================================================
          4. Audio Tracks (BGM + Dog Inner Voice + Sound Effects)
         ======================================================== */}
      {/* 4-1. Live Sound (花火の生音・炸裂音・歓声) */}
      {(theme as any)?.live_audio && (
        <Audio
          src={staticFile((theme as any).live_audio)}
          volume={((theme as any).live_volume ?? 0.85) * audioFade}
        />
      )}

      {/* 4-2. Background Music (Claude-DSP Studio BGM) */}
      {theme?.bgm_track && (
        <Audio
          src={staticFile(theme.bgm_track)}
          volume={(theme.bgm_volume ?? 0.22) * audioFade}
        />
      )}

      {/* 4-2. Unified Girl Dog Inner Voice (Irodori-TTS) */}
      {scenes.map((scene: any, idx: number) => {
        if (!scene.narration?.audio_file) return null;
        const startFrame =
          scene.start_frame + (scene.narration.start_offset_frame ?? 0);
        return (
          <Sequence
            key={`narration-${idx}`}
            from={startFrame}
            durationInFrames={scene.duration_frames}
          >
            <Audio src={staticFile(scene.narration.audio_file)} volume={1.0} />
          </Sequence>
        );
      })}

      {/* 4-3. Synchronized JIZURA-style Sound Effects (SE) */}
      {scenes.flatMap((scene: any, sIdx: number) =>
        (scene.se ?? []).map((seItem: any, seIdx: number) => {
          const startFrame = scene.start_frame + (seItem.start_offset ?? 0);
          return (
            <Sequence
              key={`se-${sIdx}-${seIdx}`}
              from={startFrame}
              durationInFrames={45}
            >
              <Audio
                src={staticFile(seItem.sound)}
                volume={seItem.volume ?? 0.7}
              />
            </Sequence>
          );
        })
      )}

      {/* ========================================================
          5. Cinematic Black Fadeout Overlay
         ======================================================== */}
      <AbsoluteFill
        style={{
          backgroundColor: "#000000",
          opacity: videoFadeOpacity,
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
