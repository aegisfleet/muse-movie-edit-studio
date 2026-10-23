# 設計メモ (docs/DESIGN.md)

本リポジトリの設計判断と、その根拠を記録する。ベース実装の詳細は元リポジトリ `movie-edit-pipeline` の README / AGENTS.md を正とする。

## 成果物仕様

- `outputs/final.mp4`: 1080×1920 (9:16)、30fps、合計尺は YAML の `project.duration_sec`（標準 30.0 秒 = 900 フレーム）、H.264 / AAC 48kHz

## 決定事項

### 1. 設定 YAML を唯一の真実とする（ベースから継承）

- Remotion コンポーネント内に動画固有のテキストを直書きしない。`run_pipeline.py` が YAML から `public/project_config.json`（開始・終了フレーム計算済み）を生成し、コンポーネントはそれをループ描画する
- 理由: エージェントが編集するのは YAML だけで済み、TypeScript の改変ミスによる合成破綻が起きない

### 2. エンコーダは実行環境で自動選択する

- `scripts/run_pipeline.py` の `select_video_encoder()` が、NVIDIA GPU デバイスの実在を確認して NVENC / libx264 を切り替える。環境変数 `VIDEO_ENCODER=nvenc|x264|auto` で上書き可能
- 理由: ffmpeg のエンコーダ一覧に `h264_nvenc` が載っていても、GPU が無い環境（Muse VM、CI、一般的なクラウド VM）では実行時エラーになる。ベース実装は NVENC 前提で、この環境では動かなかった

### 3. ナレーションは Muse の Meta AI TTS を第一候補とする

- `scripts/generate_narration.py` がバックエンドを自動選択する。Muse 環境（`/opt/hatch/bin/tts` が存在）では Meta AI ボイスで合成し、それ以外では edge-tts（日本語ボイス）を使う
- 理由: ベースの Irodori-TTS はローカルモデルと参照音声がリポジトリ外管理で、軽量な VM では実行が重い。Meta AI TTS は Muse 環境に組み込み済みで追加セットアップが不要。固定ボイス ID を使うことで「シーンごとに別人の声になる」問題を避ける
- 尺ガードレール（無音トリム + `atempo` 圧縮 + 末尾フェード）はベースの Irodori 実装から継承した

### 4. 音楽 (BGM) は生成 AI に寄せない

- BGM は実音サンプラー + DSP の `generate_sampler_bgm.py`、または素材持ち込みとする
- 理由: Meta の生成モデルには音楽のみを単独生成する経路がない（映像付き短尺クリップの生成音はあるが、BGM トラックとして分離できない）。DSP 生成は再現性があり、音響品質の設計（リバーブ、ディレイ、ヒューマナイズ）もベースで確立している

### 5. 検証はローカル CV で行い、LLM の目視に依存しない（ベースから継承）

- Gate 1（レンダリング前）と Gate 2（最終成果物）で `verify_composition.py` が被写体の中央オフセット、サイズ占有率、鮮鋭度を判定する
- Muse 環境では補助として、エージェントが抽出フレーム画像を数枚だけ目視確認する運用も可能だが、主判定はローカル指標に置く

### 6. 素材と生成物は Git 管理しない

- `inputs/`、`public/audio/`、`outputs/`、モデル重み（`*.pt`）は `.gitignore` で除外する。リポジトリはコードと設定（YAML / JSON）のみを管理する
- Muse 環境では素材の受け渡しをチャット添付、写真ライブラリ、接続デバイス経由で行い、作業コピー内の `inputs/` に配置する

## Muse 環境の実測値 (2026-10-23)

- OS: Ubuntu 24.04 (x86_64)、2 vCPU、RAM 7.7GB、ディスク 100GB
- Node.js 24.22.1 / npm 10.9.4 / Python 3.12.3
- ffmpeg 8.1.2: `zscale` / `xfade` / `tonemap` / `libx264` あり。`h264_nvenc` はビルドに含まれるが GPU デバイスなし
- 日本語フォント: Noto CJK 導入済み
- Remotion のレンダリングには Headless Chrome が必要。環境に無い場合は Remotion が初回に自動取得する
- 移植検証の実測 (2026-10-23、テストパターン素材 6 秒・単一シーン): Step 1 (ffmpeg / libx264) 約 15 秒、Step 2 (Remotion 180 フレーム、初回バンドル・ブラウザ取得込み) 約 95 秒、出力は 1080×1920 / 6.000 秒で仕様一致。`tsc --noEmit` も通過。30 秒本番 (900 フレーム) のレンダリングは概ね 5 から 8 分が見込み
- 検証で判明した不具合 2 件を移植時に修正済み: (1) SDR 入力を HLG 用 zscale チェーンに通すと "no path between colorspaces" で失敗する → 転送特性でチェーンを分岐。(2) project_config.json の型推論が設定内容に依存し、任意項目 (narration 等) で型エラーになる → scenes / theme を any として扱い、コールバック引数に型注釈を付けた

## 未決定・今後の検討

- YOLOv8 解析の CPU 運用可否（yolov8n + サンプリング間引きでの実測）
- BGM サンプル音源の公開可能な調達方法（現状は利用者持ち込み）
- Showcase Composition（波形ビジュアライザー等）の公開版への再収録
