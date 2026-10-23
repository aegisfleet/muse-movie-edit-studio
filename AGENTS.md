# AI Agent Operational Guidelines (AGENTS.md)

本ドキュメントは、AIエージェント（Muse 等）が本リポジトリで動画編集タスクを自律的かつ再現性高く遂行するための標準運用手順書である。元リポジトリ `movie-edit-pipeline` の AGENTS.md を、Linux / Muse 環境向けに移植した。

---

## 成果物仕様

- 出力: `outputs/final.mp4`（または YAML の `project.output_video`）
- 形式: 1080×1920 (9:16)、30fps、尺は YAML の合計（標準 30.0 秒 = 900 フレーム）、H.264 / AAC 48kHz

## 動作環境と基本ルール

1. OS・シェル: Linux / bash を標準とする。Windows では PowerShell でも実行可能（スクリプト側で OS 分岐済み）
2. エンコーダ: `run_pipeline.py` が GPU の実在で NVENC / libx264 を自動選択する。手動で ffmpeg コマンドを組む場合も、GPU が無い環境で `h264_nvenc` を指定しない
3. Git コミットメッセージは日本語で記述する
4. 素材（動画・音声）と生成物は Git にコミットしない（`.gitignore` 済み）。管理対象はコードと設定ファイルのみ

## 汎用ワークフロー（2段階ゲート制）

```text
Step 1: 入力素材の自動解析 (scripts/analyze_subject.py)
- YOLOv8 による被写体検出・品質スコア・最適 crop_x 算出
- 解析依存が無い環境では ffprobe とフレーム抽出で代替し、その旨を報告する
Step 2: 設定ファイル作成 (config/<video_name>.yaml)
- 合計尺が目標秒数に一致するようシーン構成を定義する
Step 2.5: 構図事前検証 (scripts/verify_composition.py --pre)
- 元動画から 9:16 切り出しをシミュレーションし、見切れ・中央ズレを事前に排除する
Step 3: ナレーション生成 (scripts/generate_narration.py --config...)
- Muse 環境では Meta AI TTS、それ以外では edge-tts が自動選択される
- 尺ガードレール (atempo) によりシーン尺内に必ず収まる
Step 4: BGM の確認 (public/audio/ に配置済みか、必要なら generate_sampler_bgm.py)
Step 5: パイプライン実行 (scripts/run_pipeline.py --config...)
- ffmpeg 切り出し・トーンマッピング・xfade 結合 → Remotion 合成
Step 6: 最終成果物の受入検査 (scripts/verify_composition.py)
- 尺の完全着地と合成破綻がないことを確認してから納品する
```

## 設計上の禁止事項・教訓（ベースから継承）

| 項目 | 決定事項 | 理由 |
|:--- |:--- |:--- |
| 構図検証 | LLM の画像認識による目視確認を主判定にしない。ローカル CV 指標で判定する | トークン消費が大きく再現性もないため |
| フレームワーク | Remotion 内に動画固有テキストを直書きしない。YAML → project_config.json のデータ駆動に徹する | 設定変更だけで別動画を作れる状態を保つため |
| 音声尺 | atempo ガードレールでシーン尺内に必ず収める | 被り・途切れを物理的に防ぐため |
| トランジション | xfade の重なり時間はスクリプトに自動計算させる | 手計算は尺ズレの原因になるため |
| 映像ノイズ除去 | CPU ヘビーな空間デノイズを組み込まない | 効果に対して処理時間が3倍に悪化するため |
| テロップ配置 | 被写体の中央をクリアに保ち、テロップは下部、装飾は外周に逃がす | 主役が見えなくなる装飾は失敗とする |
| ナレーション声質 | 固定ボイス ID で全編統一する | シーンごとの声のブレは没入感を壊すため |

## Muse 環境での素材受け渡し

- ユーザーがチャットに添付した画像・動画、写真ライブラリ、接続デバイス（スマートフォン等）から素材を受け取り、`inputs/` に配置して YAML の `input_video` / シーン別 `video` に指定する
- 生成した `outputs/final.mp4` はチャットに添付して納品する
- 処理が長尺・高解像度で重い場合は、先に短尺サンプルでレンダリング時間を実測してから本番を実行する

## クイックコマンドリファレンス

```bash
# 被写体解析 (任意、requirements-analysis.txt が必要)
python scripts/analyze_subject.py --video inputs/<video>.mp4 --target dog --interval 1.0

# Gate 1: レンダリング前の構図検証
python scripts/verify_composition.py --config config/<name>.yaml --pre

# ナレーション生成 (Meta AI TTS / edge-tts 自動選択)
python scripts/generate_narration.py --config config/<name>.yaml

# パイプライン完全実行
python scripts/run_pipeline.py --config config/<name>.yaml

# Gate 2: 最終成果物の受入検査
python scripts/verify_composition.py --config config/<name>.yaml

# Remotion プレビュー
npm start
```
