# AI Agent Operational Guidelines (AGENTS.md)

本ドキュメントは、AIエージェント（Muse 等）が本リポジトリで動画編集タスクを自律的かつ再現性高く遂行するための標準運用手順書である。Linux / Muse 環境での実行を前提とする。

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
Step 0: コンセプト提案 (エージェント → 利用者)
- 素材を受け取ったら制作に入る前に、動画のコンセプトを利用者に提案し、選択を得る
- 提案には最低限、テーマ/タイトル案、被写体のペルソナとナレーションの声 (性別・年齢感。サンプル音声を添えると確実)、テロップのトーン、BGM の方向性を含める
- 被写体の性別等の設定は利用者に確認する (例: このポメラニアンはメスなので女の子の声を当てる)
Step 1: 入力素材の自動解析 (scripts/analyze_subject.py)
- YOLOv8 による被写体検出・品質スコア・最適 crop_x 算出
- 解析は原画に対して直接行うのが標準 (軽量化の主手段はサンプリング間隔の調整)。低解像度プロキシを使う `--proxy` オプションも用意されているが、実測では生成コスト (4K 260秒で約10.5分) が大きく、同一素材の解析を約4回 / Step 1 レンダリングを約3回以上繰り返す場合にのみ元が取れるため、標準手順には含めない (docs/DESIGN.md 決定事項 7 の実測を参照)。レンダリング前の確認はプロキシではなく Gate 1 (約30秒) で行う
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

## 設計上の禁止事項・教訓

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
- **100MB を超える動画はチャットに添付できない**（web版の上限は動画 約100MB、その他 約25MB）。その場合は外部ストレージ経由で受け取ること
  - Google Drive（推奨）: 連携機能で対象ファイルを `inputs/` へ直接ダウンロードする。置き場所の例: マイドライブ / `Muse` / `inputs`。取得後はサイズとチェックサムで完全性を確認する
  - BOX、Dropbox 等: 共有リンクからダウンロードして `inputs/` に配置する
  - 使う範囲だけトリミングされた素材であれば、100MB 未満のチャット添付でも受け取れる
- 生成した `outputs/final.mp4` はチャットに添付して納品する
- 処理が長尺・高解像度で重い場合は、先に短尺サンプルでレンダリング時間を実測してから本番を実行する

## クイックコマンドリファレンス

```bash
# 被写体解析 (任意、requirements-analysis.txt が必要)
python scripts/analyze_subject.py --video inputs/<video>.mp4 --target dog --interval 3.0

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
