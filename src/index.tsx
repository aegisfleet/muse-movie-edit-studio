import React from "react";
import { registerRoot, Composition } from "remotion";
import { ShortVideo } from "./Composition";

import projectConfig from "../public/project_config.json";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ShortVideo"
        component={ShortVideo}
        durationInFrames={projectConfig.total_frames ?? 900}
        fps={projectConfig.project?.target_fps ?? 30}
        width={1080}
        height={1920}
      />
    </>
  );
};

registerRoot(RemotionRoot);
