# Muse Movie Edit Studio

アップロードした写真・動画素材から、SNS向けの縦型ショート動画（1080×1920 / 30fps）を自動編集するパイプライン。AIエージェント **Muse** の環境で使うことを第一に設計し、通常の Linux / Windows 環境でも単体で動作する。

ベースは [aegisfleet/movie-edit-pipeline](https://github.com/aegisfleet/movie-edit-pipeline)（非公開版）で、本リポジトリはその Muse 対応・公開版である。

## 何ができるか

- 設定ファイル（YAML）を唯一の真実とするデータ駆動編集。コードを書き換えずに YAML の差し替えだけで別動画が作れる
- ffmpeg による切り出し、HLG（BT.2020）→ Rec.709 トーンマッピング（`zscale` + `tonemap=hable`）、シーン別カラーグレーディング、動的 `xfade` トランジション
- Remotion（React）による JIZURA 風フローティングテロップ、外周装飾フレーム、パーティクル、効果音のタイムライン同期
- ナレーション自動生成: Muse 環境では **Meta AI ボイスの TTS**、環境外では edge-tts に自動フォールバック。尺を超えた音声は `atempo` ガードレールで自動調整
- YOLOv8 による被写体解析と最適クロップ位置（`crop_x`）の自動算出、レンダリング前後の2段階品質ゲート（LLM の画像認識を使わないローカル検証）
- 任意の合計尺に対応（標準は 30.0 秒 = 900 フレーム）

## アーキテクチャ

```text
config/<name>.yaml   ← 唯一の真実 (シーン構成・テロップ・ナレーション・色調)
      │
      ├─ scripts/analyze_subject.py     被写体解析 → ハイライトと crop_x を提案
      ├─ scripts/verify_composition.py --pre   Gate 1: レンダリング前の構図検証
      ├─ scripts/generate_narration.py  ナレーション音声を public/audio/ へ生成
      ├─ scripts/generate_sampler_bgm.py (任意) 実音サンプラー + DSP の BGM 生成
      ▼
scripts/run_pipeline.py
      ├─ Step 1: ffmpeg で背景動画を生成 → public/background_30s.mp4
      │          YAML → public/project_config.json (フレーム計算済み) も出力
      └─ Step 2: Remotion で合成 → outputs/final.mp4
      ▼
scripts/verify_composition.py           Gate 2: 最終成果物の受入検査
```

## クイックスタート

前提: Node.js 20+、Python 3.11+、ffmpeg（`zscale` / `xfade` / `tonemap` / `libx264` を含むビルド。GPU がある環境では NVENC も自動利用）

```bash
git clone https://github.com/aegisfleet/muse-movie-edit-studio.git
cd muse-movie-edit-studio
npm ci
pip install -r requirements.txt        # 解析も使う場合は requirements-analysis.txt
cp config/fireworks.yaml config/my_video.yaml   # 設定を作成し、素材に合わせて編集
# 素材を inputs/ に配置 (Git には含めない)
python scripts/generate_narration.py --config config/my_video.yaml   # ナレーション (任意)
python scripts/run_pipeline.py --config config/my_video.yaml
# → outputs/final.mp4
npm start   # Remotion のブラウザプレビュー
```

Muse 環境では、エージェントに素材（チャット添付・写真ライブラリ・接続デバイス）を渡して「この素材で30秒の縦型ショートを作って」と依頼するだけで、上記の全手順をエージェントが実行する。エージェント向けの標準手順は [AGENTS.md](AGENTS.md)、設計判断は [docs/DESIGN.md](docs/DESIGN.md) を参照。

## Muse 版での主な変更点（ベースとの差分）

| 項目 | ベース (movie-edit-pipeline) | 本リポジトリ |
| :--- | :--- | :--- |
| 実行環境 | Windows / PowerShell + NVENC 前提 | Linux / bash 対応。GPU が無い環境では `libx264` に自動フォールバック (`VIDEO_ENCODER` で明示可) |
| ナレーション | Irodori-TTS（ローカルモデル必須） | Muse の Meta AI TTS を第一候補、edge-tts を汎用フォールバックとする `generate_narration.py` |
| Python 依存 | requirements なし | `requirements.txt`（コア）/ `requirements-analysis.txt`（解析）に分離して固定 |
| Remotion 合成 | Showcase 含む3 Composition | 公開版は本編 `ShortVideo` のみに整理 |
| レンダリング設定 | concurrency=4 / gl=angle 固定 | CPU 数に応じた concurrency、OS 別の GL 既定 (`REMOTION_CONCURRENCY` / `REMOTION_GL` で上書き可) |

## 設定ファイルの書き方

`config/fireworks.yaml`（花火・生音ブースト）と `config/gx010098.yaml`（ペット・ナレーション付き）が実例。各シーンに `start_time` / `duration_sec` / `crop_x` / `profile`（ffmpeg の色調フィルタ）/ `subtitles` / `narration`（`text` と `audio_file`）などを記述し、合計が目標尺になるよう構成する。

## 注意事項

- 素材動画・音声・生成物は `.gitignore` で除外している。リポジトリで管理するのはコードと設定のみ
- BGM サンプラー（`generate_sampler_bgm.py`）は生音 PCM サンプルを `public/audio/` 配下に別途配置した場合に動作する
- ナレーションの声質はバックエンド依存。Muse の Meta AI ボイスは固定ボイス ID で全編統一する

## ライセンス

MIT（[LICENSE](LICENSE)）
