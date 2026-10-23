# Muse Movie Edit Studio

アップロードした写真・動画素材から、SNS向けの縦型ショート動画（1080×1920 / 30fps）を自動編集するパイプライン。AIエージェント **Muse** の環境で使うことを第一に設計し、通常の Linux / Windows 環境でも単体で動作する。


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

Muse 環境では、エージェントに素材を渡して「この素材で30秒の縦型ショートを作って」と依頼するだけで、上記の全手順をエージェントが実行する。エージェント向けの標準手順は [AGENTS.md](AGENTS.md)、設計判断は [docs/DESIGN.md](docs/DESIGN.md) を参照。

## 素材ファイルの受け渡し（重要）

Muse のチャット添付にはサイズ上限がある（web版では動画が約100MB、その他のファイルは約25MB）。**100MB を超える動画ファイルはチャットに直接アップロードできない**ため、外部ストレージを経由すること。

- **Google Drive（推奨）**: Drive に素材を置けば、Muse が連携機能で作業領域へ直接ダウンロードできる。上限は実質的に作業領域のディスク容量で、GB 級のファイルでも受け渡せる（実測: 1.42GB の GoPro 動画を取得し、チェックサム一致まで確認済み）。置き場所の例: マイドライブ / `Muse` / `inputs`
- **その他の外部ストレージ**: BOX、Dropbox 等の共有リンクを渡してもらえれば、Muse がリンク先からダウンロードして受け取る
- **小さい素材**: 使う範囲だけを事前にトリミングして 100MB 未満に収めれば、チャット添付でも渡せる

受け取った素材は作業コピーの `inputs/` に配置され、Git には含まれない（成果物の受け渡しも同様に、チャット添付または外部ストレージ経由で行う）。

## 処理時間の目安とプロキシについて

パターン別の処理時間（本番 HD / SD / 確認用 / 最速、工程別の実測）は [docs/DESIGN.md](docs/DESIGN.md) の「処理時間の目安（パターン別）」に集約している。要点だけ挙げると:

- 本番 HD（1080×1920）のレンダリングは約15分。確認用レンダーは解像度と色変換の省略で約4から6分まで落とせる
- 被写体解析には低解像度プロキシを使う `--proxy` オプションがあるが、生成（初回のみ約10.5分）が先行コストになるため標準手順には含めていない。同一素材を何度も解析・レンダリングする場合のみ検討する（詳細は DESIGN.md 決定事項 7）

## 設計上の特徴

| 項目 | 本リポジトリの方針 |
| :--- | :--- |
| 実行環境 | Muse 環境（Linux / bash）を標準とする。GPU が無い環境では `libx264` に自動フォールバックし、Windows + NVENC 環境でもそのまま動く (`VIDEO_ENCODER` で明示可) |
| ナレーション | Muse の Meta AI TTS を第一候補とし、Muse 環境外では edge-tts に自動フォールバックする `generate_narration.py` |
| Python 依存 | `requirements.txt`（コア）と `requirements-analysis.txt`（解析用）に分離。重い解析依存は必要な場合だけ入れる |
| Remotion 合成 | 本編 `ShortVideo` Composition に集中し、演出はすべて YAML 駆動にする |
| レンダリング設定 | CPU 数に応じた concurrency と OS 別の GL 既定を自動選択する (`REMOTION_CONCURRENCY` / `REMOTION_GL` で上書き可) |

## 設定ファイルの書き方

`config/fireworks.yaml`（花火・生音ブースト）と `config/gx010098.yaml`（ペット・ナレーション付き）が実例。各シーンに `start_time` / `duration_sec` / `crop_x` / `profile`（ffmpeg の色調フィルタ）/ `subtitles` / `narration`（`text` と `audio_file`）などを記述し、合計が目標尺になるよう構成する。

## 注意事項

- 素材動画・音声・生成物は `.gitignore` で除外している。リポジトリで管理するのはコードと設定のみ
- BGM サンプラー（`generate_sampler_bgm.py`）は生音 PCM サンプルを `public/audio/` 配下に別途配置した場合に動作する
- ナレーションの声質はバックエンド依存。Muse の Meta AI ボイスは固定ボイス ID で全編統一する

## ライセンス

MIT（[LICENSE](LICENSE)）
