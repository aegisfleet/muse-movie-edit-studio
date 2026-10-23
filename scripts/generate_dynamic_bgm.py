"""
Consistent 30-Second Acoustic Pop BGM Generator
- 30秒間を通して一貫したメロディ・テンポ・グルーヴ（BPM 120）を維持
- シーン毎のぶつ切り感を無くし、動画全体に統一感と心地よい躍動感を与える
- マリンバ、ピチカート、ウッドベース、ソフトパーカッション（シェイカー・ウッドブロック・キック）
- 28.0秒〜30.0秒で綺麗に解決・完結するエンドジングル
"""

import numpy as np
import wave
from pathlib import Path

def create_consistent_30s_bgm(output_path: Path):
    sr = 44100
    total_sec = 30.0
    total_samples = int(sr * total_sec)
    
    # ステレオバッファ
    left = np.zeros(total_samples, dtype=np.float32)
    right = np.zeros(total_samples, dtype=np.float32)

    def note_to_freq(note_name: str) -> float:
        names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = int(note_name[-1])
        pitch = note_name[:-1]
        semitone = names.index(pitch)
        midi = (octave + 1) * 12 + semitone
        return 440.0 * (2.0 ** ((midi - 69) / 12.0))

    def add_tone(track_l, track_r, start_sec, dur_sec, freq, volume=0.5, pan=0.0, instrument='marimba'):
        idx_start = int(start_sec * sr)
        idx_len = int(dur_sec * sr)
        if idx_start >= total_samples or idx_len <= 0:
            return
        actual_len = min(idx_len, total_samples - idx_start)
        t = np.linspace(0, actual_len / sr, actual_len, endpoint=False)

        if instrument == 'marimba':
            # マリンバ：打撃アタック＋豊かな倍音＋自然な減衰
            env = np.exp(-t * (8.5 + 2.5 * (freq / 440.0)))
            wave_sig = (
                np.sin(2 * np.pi * freq * t) * 1.0 +
                np.sin(2 * np.pi * freq * 2.76 * t) * 0.3 * np.exp(-t * 18.0) +
                np.sin(2 * np.pi * freq * 4.0 * t) * 0.12 * np.exp(-t * 26.0)
            )
            sig = wave_sig * env * volume
        elif instrument == 'pizzicato':
            # 弦ピチカート：丸みのあるポロロン感
            env = np.exp(-t * 6.5)
            sig = (
                np.sin(2 * np.pi * freq * t) * 1.0 +
                np.sin(2 * np.pi * freq * 2 * t) * 0.35 +
                np.sin(2 * np.pi * freq * 3 * t) * 0.15
            ) * env * volume
        elif instrument == 'bass':
            # ウッドベース：温かい低域
            env = np.exp(-t * 4.0)
            sig = (
                np.sin(2 * np.pi * freq * t) * 1.0 +
                np.sin(2 * np.pi * freq * 2 * t) * 0.45 +
                np.sin(2 * np.pi * freq * 3 * t) * 0.15
            ) * env * volume
        elif instrument == 'glock':
            # グロッケン：キラキラした高音の余韻
            env = np.exp(-t * 4.2)
            sig = (
                np.sin(2 * np.pi * freq * t) * 1.0 +
                np.sin(2 * np.pi * freq * 3.0 * t) * 0.25
            ) * env * volume
        else:
            env = np.exp(-t * 6.0)
            sig = np.sin(2 * np.pi * freq * t) * env * volume

        pan_l = 0.5 * (1.0 - pan)
        pan_r = 0.5 * (1.0 + pan)
        track_l[idx_start:idx_start + actual_len] += sig * pan_l
        track_r[idx_start:idx_start + actual_len] += sig * pan_r

    def add_percussion(track_l, track_r, start_sec, kind='pop', volume=0.4, pan=0.0):
        idx_start = int(start_sec * sr)
        dur_sec = 0.18
        idx_len = int(dur_sec * sr)
        if idx_start >= total_samples:
            return
        actual_len = min(idx_len, total_samples - idx_start)
        t = np.linspace(0, actual_len / sr, actual_len, endpoint=False)

        if kind == 'kick':
            # ソフトで温かいアコースティックキック
            f_env = np.linspace(130, 42, actual_len)
            sig = np.sin(2 * np.pi * f_env * t) * np.exp(-t * 22.0) * volume * 1.1
        elif kind == 'shaker':
            # 軽やかなシェイカー
            sig = (np.random.rand(actual_len) * 2 - 1) * np.exp(-t * 32.0) * volume * 0.35
        elif kind == 'woodblock':
            # コロコロしたウッドブロック
            sig = np.sin(2 * np.pi * 920 * t) * np.exp(-t * 38.0) * volume * 0.75
        elif kind == 'cymbal':
            noise = (np.random.rand(actual_len) * 2 - 1)
            sig = noise * np.exp(-t * 7.5) * volume * 0.55
        else:
            sig = np.sin(2 * np.pi * 750 * t) * np.exp(-t * 28.0) * volume

        pan_l = 0.5 * (1.0 - pan)
        pan_r = 0.5 * (1.0 + pan)
        track_l[idx_start:idx_start + actual_len] += sig * pan_l
        track_r[idx_start:idx_start + actual_len] += sig * pan_r

    # ========================================================
    # 統一テンポ: BPM 120 (1拍 = 0.5s, 1小節 = 2.0s, 計15小節 = 30.0s)
    # ========================================================
    bpm = 120.0
    beat = 60.0 / bpm  # 0.5s
    eighth = beat / 2.0  # 0.25s
    sixteenth = beat / 4.0  # 0.125s

    # コード進行（15小節）:
    # 0s - 8s (小節 1-4): C -> G/B -> Am7 -> G
    # 8s - 16s (小節 5-8): F -> C/E -> Dm7 -> G7
    # 16s - 24s (小節 9-12): C -> G/B -> Am7 -> F
    # 24s - 28s (小節 13-14): Dm7 -> G7 -> Em7 -> Am7
    # 28s - 30s (小節 15): Cmaj9 解決
    chords = [
        # (root, bass, [chord notes])
        ('C4', 'C3', ['E4', 'G4', 'C5']),
        ('G4', 'B2', ['D4', 'G4', 'B4']),
        ('A4', 'A2', ['C4', 'E4', 'A4']),
        ('G4', 'G2', ['B3', 'D4', 'G4']),

        ('F4', 'F2', ['A3', 'C4', 'F4']),
        ('E4', 'E2', ['G3', 'C4', 'E4']),
        ('D4', 'D2', ['F3', 'A3', 'D4']),
        ('G4', 'G2', ['B3', 'D4', 'G4']),

        ('C4', 'C3', ['E4', 'G4', 'C5']),
        ('G4', 'B2', ['D4', 'G4', 'B4']),
        ('A4', 'A2', ['C4', 'E4', 'A4']),
        ('F4', 'F2', ['A3', 'C4', 'F4']),

        ('D4', 'D2', ['F3', 'A3', 'C4']),
        ('G4', 'G2', ['B3', 'D4', 'G4']),
    ]

    # メインメロディ（14小節分：親しみやすく躍動感のある統一メロディ）
    # (小節index, 拍offset, 音名, 長さ, 音量)
    melody_notes = [
        # 小節 1 (C): タラララ〜♪
        (0, 0.0, 'E5', 0.4, 0.38), (0, 0.5, 'G5', 0.4, 0.38), (0, 1.0, 'C6', 0.6, 0.42), (0, 1.5, 'B5', 0.35, 0.35),
        # 小節 2 (G/B):
        (1, 0.0, 'D5', 0.4, 0.38), (1, 0.5, 'G5', 0.4, 0.38), (1, 1.0, 'B5', 0.7, 0.40),
        # 小節 3 (Am7):
        (2, 0.0, 'C5', 0.4, 0.38), (2, 0.5, 'E5', 0.4, 0.38), (2, 1.0, 'A5', 0.6, 0.42), (2, 1.5, 'G5', 0.35, 0.35),
        # 小節 4 (G):
        (3, 0.0, 'B4', 0.4, 0.35), (3, 0.5, 'D5', 0.4, 0.38), (3, 1.0, 'G5', 0.8, 0.40),

        # 小節 5 (F): 軽やかにステップ
        (4, 0.0, 'A5', 0.45, 0.42), (4, 0.5, 'C6', 0.4, 0.42), (4, 1.0, 'F6', 0.6, 0.45), (4, 1.5, 'E6', 0.35, 0.38),
        # 小節 6 (C/E):
        (5, 0.0, 'G5', 0.45, 0.40), (5, 0.5, 'C6', 0.4, 0.40), (5, 1.0, 'E6', 0.7, 0.42),
        # 小節 7 (Dm7):
        (6, 0.0, 'F5', 0.4, 0.38), (6, 0.5, 'A5', 0.4, 0.40), (6, 1.0, 'D6', 0.55, 0.42), (6, 1.5, 'C6', 0.35, 0.38),
        # 小節 8 (G7): ターンしてサビへ
        (7, 0.0, 'B5', 0.45, 0.40), (7, 0.5, 'A5', 0.35, 0.38), (7, 1.0, 'G5', 0.4, 0.40), (7, 1.5, 'D6', 0.45, 0.42),

        # 小節 9 (C): サビ・さらに伸びやかに
        (8, 0.0, 'E6', 0.5, 0.46), (8, 0.5, 'D6', 0.35, 0.40), (8, 1.0, 'C6', 0.55, 0.45), (8, 1.5, 'G5', 0.35, 0.38),
        # 小節 10 (G/B):
        (9, 0.0, 'D6', 0.5, 0.45), (9, 0.5, 'C6', 0.35, 0.40), (9, 1.0, 'B5', 0.6, 0.42),
        # 小節 11 (Am7):
        (10, 0.0, 'C6', 0.5, 0.45), (10, 0.5, 'B5', 0.35, 0.38), (10, 1.0, 'A5', 0.55, 0.42), (10, 1.5, 'E5', 0.35, 0.36),
        # 小節 12 (F):
        (11, 0.0, 'A5', 0.45, 0.42), (11, 0.5, 'C6', 0.4, 0.42), (11, 1.0, 'F6', 0.7, 0.46),

        # 小節 13 (Dm7): クライマックスへ駆け上がる
        (12, 0.0, 'F5', 0.35, 0.40), (12, 0.5, 'A5', 0.35, 0.42), (12, 1.0, 'C6', 0.4, 0.44), (12, 1.5, 'D6', 0.4, 0.46),
        # 小節 14 (G7): フィナーレ準備
        (13, 0.0, 'E6', 0.45, 0.46), (13, 0.5, 'D6', 0.45, 0.46), (13, 1.0, 'B5', 0.5, 0.45), (13, 1.5, 'G5', 0.4, 0.42),
    ]

    # 1. リズム・ベース・伴奏ループ（全14小節 = 28秒間一貫）
    for m in range(14):
        m_start = m * 2.0  # 1小節 = 2.0秒
        chord_root, bass_note, c_notes = chords[m]

        # 4拍分のリズム＆ベース
        for b in range(4):
            t_beat = m_start + b * beat

            # リズム隊（全編一貫した軽快なオーガニック・グルーヴ）
            if b % 2 == 0:
                # 1拍目・3拍目: ソフトキック
                add_percussion(left, right, t_beat, kind='kick', volume=0.45, pan=-0.1)
            # 2拍目・4拍目: ウッドブロック（スネア代わりの心地よいバックビート）
            if b % 2 == 1:
                add_percussion(left, right, t_beat, kind='woodblock', volume=0.42, pan=0.15)

            # 8分音符裏のシェイカー（常時スウィング感を維持）
            add_percussion(left, right, t_beat, kind='shaker', volume=0.22, pan=0.2)
            add_percussion(left, right, t_beat + eighth, kind='shaker', volume=0.26, pan=-0.2)

            # ベース（1拍目・3拍目はルート／5度）
            if b == 0:
                add_tone(left, right, t_beat, 0.45, note_to_freq(bass_note), volume=0.48, pan=-0.25, instrument='bass')
            elif b == 2:
                # 5度またはオクターブ
                add_tone(left, right, t_beat, 0.45, note_to_freq(bass_note) * 1.5, volume=0.40, pan=-0.25, instrument='bass')
            elif b == 3:
                # つなぎのウォーキングベース
                add_tone(left, right, t_beat + eighth, 0.22, note_to_freq(bass_note) * 1.12, volume=0.35, pan=-0.25, instrument='bass')

            # 伴奏ピチカート・アルペジオ（ポロロンと一定のパターンで寄り添う）
            cn = c_notes[b % len(c_notes)]
            add_tone(left, right, t_beat + eighth * 0.5, 0.25, note_to_freq(cn), volume=0.26, pan=0.25 if b % 2 == 0 else -0.2, instrument='pizzicato')

    # 2. メインメロディの配置（マリンバ＋ベル）
    for m, b_offset, n_name, dur, vol in melody_notes:
        t_note = m * 2.0 + b_offset
        freq = note_to_freq(n_name)
        # 主旋律マリンバ
        add_tone(left, right, t_note, dur, freq, volume=vol, pan=0.1, instrument='marimba')
        # グロッケン（要所でキラキラ感を添える）
        if '6' in n_name or b_offset == 0.0:
            add_tone(left, right, t_note, dur * 1.2, freq, volume=vol * 0.45, pan=-0.15, instrument='glock')

    # 3. 28.0秒〜30.0秒: ★30秒ジャスト解決の終止ジングル（Cmaj9 Perfect Cadence）★
    # 28.1s, 28.3s, 28.5s, 28.7s: 駆け上がりチャイム
    fill_notes = [('G5', 28.1), ('A5', 28.3), ('B5', 28.5), ('D6', 28.7)]
    for note, pt in fill_notes:
        add_tone(left, right, pt, 0.2, note_to_freq(note), volume=0.42, pan=0.0, instrument='marimba')
        add_percussion(left, right, pt, kind='woodblock', volume=0.45)

    # 28.9s: 最終解決和音 Cmaj9 (C3, G3, C4, E4, G4, B4, D5, E5)
    # 30秒ジャストまで豊かに広がり、優しく完結する
    add_percussion(left, right, 28.9, kind='cymbal', volume=0.75)
    add_percussion(left, right, 28.9, kind='kick', volume=0.65)

    cadence_notes = ['C3', 'G3', 'C4', 'E4', 'G4', 'B4', 'D5', 'E5']
    for i, cn in enumerate(cadence_notes):
        add_tone(left, right, 28.9, 1.1, note_to_freq(cn), volume=0.42, pan=0.12 * (i - 3.5), instrument='glock')
        add_tone(left, right, 28.9, 1.1, note_to_freq(cn), volume=0.38, pan=-0.08 * (i - 3.5), instrument='marimba')

    # ノーマライズ＆クリッピング防止
    max_val = max(np.max(np.abs(left)), np.max(np.abs(right)))
    if max_val > 0:
        left = (left / max_val) * 0.85
        right = (right / max_val) * 0.85

    # 29.85sから30.0sにかけて微小フェードアウト
    fade_len = int(sr * 0.15)
    fade_curve = np.linspace(1.0, 0.0, fade_len)
    left[-fade_len:] *= fade_curve
    right[-fade_len:] *= fade_curve

    # 16-bit PCM WAVとして書き出し
    left_16 = (left * 32767).astype(np.int16)
    right_16 = (right * 32767).astype(np.int16)
    stereo = np.empty((total_samples * 2,), dtype=np.int16)
    stereo[0::2] = left_16
    stereo[1::2] = right_16

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())

    print(f"Generated consistent 30s acoustic pop BGM -> {output_path}")

if __name__ == "__main__":
    out_file = Path("public/audio/bgm_dynamic_30s.wav")
    create_consistent_30s_bgm(out_file)
