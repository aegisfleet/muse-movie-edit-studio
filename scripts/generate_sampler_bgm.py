"""
Advanced Studio-Grade Acoustic Lo-Fi BGM Composer
Inspired by Claude's Web Audio / Modern Procedural Music Architecture & Sharou's Lo-Fi Aesthetic
- 実音サンプラー（生ピアノ、生ギター、木琴、ウッドベース、生ドラム）
- プロ仕様の空間オーディオDSP処理:
    1. FFTコンボリューション・スタジオプレートリバーブ（豊かな空間の広がり）
    2. ピンポン・ステレオディレイ（メロディの浮遊感）
    3. アナログ・ウォームフィルター（耳に優しいまろやかなLo-Fiトーン）
    4. ストローク・ヒューマナイズ（15〜25msの時間差ポロロンストローク）
    5. キック連動サイドチェーン・ダッキング（心地よいビートのうねり）
- しゃろう風 王道コード進行 (Fmaj7 -> G7 -> Em7 -> Am7) & BPM 116 スウィング
"""

import wave
import numpy as np
from pathlib import Path

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def note_to_midi(note_str: str) -> int:
    pitch = note_str[:-1]
    octave = int(note_str[-1])
    semitone = NOTE_NAMES.index(pitch)
    return (octave + 1) * 12 + semitone

class AdvancedStudioSampler:
    def __init__(self, sample_dir: Path):
        self.sample_dir = sample_dir
        self.samples = {}
        self.sr = 44100
        self._load_samples()

    def _read_wav(self, path: Path) -> np.ndarray:
        with wave.open(str(path), 'rb') as wf:
            self.sr = wf.getframerate()
            n_ch = wf.getnchannels()
            frames = wf.readframes(wf.getnframes())
            data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            if n_ch == 2:
                return data.reshape(-1, 2)
            return np.stack([data, data], axis=-1)

    def _load_samples(self):
        # ピアノ
        self.samples['piano'] = {}
        piano_notes = ['C4', 'D4', 'F4', 'G4', 'A4', 'C5', 'D5', 'E5', 'G5']
        for n in piano_notes:
            f = self.sample_dir / f'piano/{n}.wav'
            if f.exists():
                self.samples['piano'][note_to_midi(n)] = self._read_wav(f)

        # ギター
        self.samples['guitar'] = {}
        for n in ['A2', 'C3', 'E3', 'A3']:
            f = self.sample_dir / f'guitar/{n}.wav'
            if f.exists():
                self.samples['guitar'][note_to_midi(n)] = self._read_wav(f)

        # 木琴・シロフォン
        self.samples['xylophone'] = {}
        for n in ['C5', 'G5', 'C6']:
            f = self.sample_dir / f'xylophone/{n}.wav'
            if f.exists():
                self.samples['xylophone'][note_to_midi(n)] = self._read_wav(f)

        # ウッドベース
        self.samples['bass'] = {}
        for n in ['C2', 'D2', 'E2', 'A2']:
            f = self.sample_dir / f'bass/{n}.wav'
            if f.exists():
                self.samples['bass'][note_to_midi(n)] = self._read_wav(f)

        # ドラム
        self.samples['kick'] = self._read_wav(self.sample_dir / 'drums/kick.wav')
        self.samples['snare'] = self._read_wav(self.sample_dir / 'drums/snare.wav')
        self.samples['hihat'] = self._read_wav(self.sample_dir / 'drums/hihat.wav')

    def get_sample(self, inst: str, target_midi: int) -> np.ndarray:
        bank = self.samples[inst]
        avail = list(bank.keys())
        closest = min(avail, key=lambda m: abs(m - target_midi))
        base = bank[closest]
        diff = target_midi - closest
        if diff == 0:
            return base.copy()

        factor = 2.0 ** (diff / 12.0)
        old_len = len(base)
        new_len = int(old_len / factor)
        if new_len <= 10:
            return base[:10]

        old_idx = np.arange(old_len)
        new_idx = np.linspace(0, old_len - 1, new_len)
        l = np.interp(new_idx, old_idx, base[:, 0])
        r = np.interp(new_idx, old_idx, base[:, 1])
        return np.stack([l, r], axis=-1)

# ========================================================
# DSP エフェクト・プロセッサー群 (Web Audio API アーキテクチャ)
# ========================================================
def apply_fft_reverb(signal: np.ndarray, sr: int = 44100, rt60: float = 1.4, wet_gain: float = 0.22) -> np.ndarray:
    """スタジオプレート風の濃密で温かいステレオインパルス応答をFFT畳み込み"""
    ir_len = int(sr * rt60)
    t = np.linspace(0, rt60, ir_len)
    decay = np.exp(-3.5 * t / rt60)

    # 左右独立のランダム散乱波（ステレオ広がり）
    np.random.seed(123)
    ir_l = (np.random.randn(ir_len) * 2 - 1) * decay
    ir_r = (np.random.randn(ir_len) * 2 - 1) * decay

    # アーリーリフレクション
    for ms, g in [(18, 0.5), (32, 0.4), (50, 0.3), (75, 0.2)]:
        idx = int(ms * 0.001 * sr)
        if idx < ir_len:
            ir_l[idx] += g
            ir_r[idx + 4] += g * 0.95

    ir_l /= np.sum(np.abs(ir_l))
    ir_r /= np.sum(np.abs(ir_r))

    sig_len = len(signal)
    fft_n = sig_len + ir_len - 1

    # FFT畳み込み (高速演算)
    sig_l_fft = np.fft.rfft(signal[:, 0], n=fft_n)
    sig_r_fft = np.fft.rfft(signal[:, 1], n=fft_n)
    ir_l_fft = np.fft.rfft(ir_l, n=fft_n)
    ir_r_fft = np.fft.rfft(ir_r, n=fft_n)

    wet_l = np.fft.irfft(sig_l_fft * ir_l_fft)[:sig_len]
    wet_r = np.fft.irfft(sig_r_fft * ir_r_fft)[:sig_len]

    dry_gain = 1.0 - (wet_gain * 0.5)
    out_l = signal[:, 0] * dry_gain + wet_l * wet_gain
    out_r = signal[:, 1] * dry_gain + wet_r * wet_gain
    return np.stack([out_l, out_r], axis=-1)

def apply_pingpong_delay(signal: np.ndarray, sr: int = 44100, delay_l_sec: float = 0.258, delay_r_sec: float = 0.387, feedback: float = 0.28, wet: float = 0.18) -> np.ndarray:
    """左右で時間差をつけて跳ねるピンポン・ステレオディレイ"""
    dl = int(delay_l_sec * sr)
    dr = int(delay_r_sec * sr)
    out = signal.copy()
    left = signal[:, 0]
    right = signal[:, 1]

    for i in range(dl, len(left)):
        out[i, 0] += right[i - dl] * feedback * wet
    for i in range(dr, len(right)):
        out[i, 1] += left[i - dr] * feedback * wet
    return out

def apply_warm_lowpass(signal: np.ndarray, alpha: float = 0.35) -> np.ndarray:
    """高域の硬いアタックをまろやかにするシングルポール・ローパスフィルター"""
    out = np.zeros_like(signal)
    out[0] = signal[0]
    for i in range(1, len(signal)):
        out[i] = out[i - 1] * alpha + signal[i] * (1.0 - alpha)
    return out

def compose_advanced_claude_style_bgm(output_path: Path):
    sample_dir = Path("assets/samples")
    sampler = AdvancedStudioSampler(sample_dir)

    sr = 44100
    total_sec = 30.0
    total_samples = int(sr * total_sec)

    # トラックごとの分離バッファ（後段で個別エフェクト適用）
    track_harmony = np.zeros((total_samples, 2), dtype=np.float32) # コード・伴奏
    track_melody = np.zeros((total_samples, 2), dtype=np.float32)  # メロディ
    track_bass = np.zeros((total_samples, 2), dtype=np.float32)    # ベース
    track_drums = np.zeros((total_samples, 2), dtype=np.float32)   # ドラム

    def add_to_track(target_track: np.ndarray, audio_data: np.ndarray, start_sec: float, volume: float = 0.5, pan: float = 0.0, max_dur: float = None):
        start_idx = int(start_sec * sr)
        if start_idx >= total_samples or start_idx < 0:
            return
        snd = audio_data.copy()
        if max_dur is not None:
            max_len = int(max_dur * sr)
            if len(snd) > max_len:
                snd = snd[:max_len]
                fade_n = min(int(0.06 * sr), max_len)
                fade = np.linspace(1.0, 0.0, fade_n)
                snd[-fade_n:, 0] *= fade
                snd[-fade_n:, 1] *= fade

        pan_l = 0.5 * (1.0 - pan)
        pan_r = 0.5 * (1.0 + pan)
        snd[:, 0] *= pan_l * volume
        snd[:, 1] *= pan_r * volume

        avail = min(len(snd), total_samples - start_idx)
        target_track[start_idx:start_idx + avail] += snd[:avail]

    # ========================================================
    # テンポ: BPM 116 (1拍 = 0.51724s, 1小節 = 2.06896s)
    # 14小節 = 28.965秒 + 15小節目頭(28.965s)に解決コードで30秒ジャスト完結！
    # ========================================================
    bpm = 116.0
    beat = 60.0 / bpm
    swing_eighth_1 = beat * 0.58
    swing_eighth_2 = beat * 0.42

    # しゃろう氏の王道コード進行（透明感とエモい浮遊感）
    sharou_chords = [
        ('Fmaj7', note_to_midi('F1'), [note_to_midi('A3'), note_to_midi('C4'), note_to_midi('E4'), note_to_midi('G4')]), # Fmaj9
        ('G7',    note_to_midi('G1'), [note_to_midi('G3'), note_to_midi('B3'), note_to_midi('D4'), note_to_midi('F4')]), # G7
        ('Em7',   note_to_midi('E1'), [note_to_midi('G3'), note_to_midi('B3'), note_to_midi('D4'), note_to_midi('G4')]), # Em7
        ('Am7',   note_to_midi('A1'), [note_to_midi('G3'), note_to_midi('C4'), note_to_midi('E4'), note_to_midi('A4')]), # Am7
    ]

    total_bars = 14
    for bar in range(total_bars):
        t_bar = bar * (4 * beat)
        chord_idx = bar % 4

        if bar == 12:
            bass_midi = note_to_midi('D2')
            voicing = [note_to_midi('F3'), note_to_midi('A3'), note_to_midi('C4'), note_to_midi('E4')]
        elif bar == 13:
            bass_midi = note_to_midi('G1')
            voicing = [note_to_midi('F3'), note_to_midi('B3'), note_to_midi('D4'), note_to_midi('G4')]
        else:
            _, bass_midi, voicing = sharou_chords[chord_idx]

        # --- ドラム ---
        for b in range(4):
            t_beat = t_bar + b * beat
            if b == 0 or b == 2:
                add_to_track(track_drums, sampler.samples['kick'], t_beat, volume=0.45, pan=-0.05)
            if b == 1 or b == 3:
                add_to_track(track_drums, sampler.samples['snare'], t_beat, volume=0.36, pan=0.1)

            add_to_track(track_drums, sampler.samples['hihat'], t_beat, volume=0.20, pan=0.2)
            add_to_track(track_drums, sampler.samples['hihat'], t_beat + swing_eighth_1, volume=0.16, pan=-0.15)

        # --- ウッドベース ---
        bass_s1 = sampler.get_sample('bass', bass_midi)
        add_to_track(track_bass, bass_s1, t_bar, volume=0.52, pan=-0.25, max_dur=beat * 1.8)

        fifth_midi = bass_midi + 7
        bass_s2 = sampler.get_sample('bass', fifth_midi)
        add_to_track(track_bass, bass_s2, t_bar + 2 * beat, volume=0.42, pan=-0.25, max_dur=beat * 1.2)

        if bar < 13:
            next_chord_idx = (bar + 1) % 4
            next_bass = sharou_chords[next_chord_idx][1]
            walk_midi = next_bass - 1 if next_bass > bass_midi else next_bass + 2
            bass_s3 = sampler.get_sample('bass', walk_midi)
            add_to_track(track_bass, bass_s3, t_bar + 3 * beat + swing_eighth_1, volume=0.35, pan=-0.25, max_dur=swing_eighth_2)

        # --- 和音コードバッキング（★ストローク・ヒューマナイズ★） ---
        # 1音あたり20msずらして「ポロロン」と人間らしく弾く
        for chord_t_rel in [swing_eighth_1, 2 * beat, 3 * beat + swing_eighth_1]:
            for vi, note_m in enumerate(voicing):
                p_s = sampler.get_sample('piano', note_m)
                strum_offset = vi * 0.022  # 22ms ストロークディレイ
                human_vel = 0.22 + np.random.uniform(-0.02, 0.02)
                pan_p = -0.15 + 0.1 * vi
                add_to_track(track_harmony, p_s, t_bar + chord_t_rel + strum_offset, volume=human_vel, pan=pan_p, max_dur=beat * 1.3)

    # ========================================================
    # 2. ★歌う主旋律（生ピアノ ＋ 木琴レイヤー）★
    # ========================================================
    melody = [
        # Aメロ
        (0, 0.0, 'C5', 0.8, 0.45), (0, swing_eighth_1 / beat, 'D5', 0.6, 0.45), (0, 1.0, 'E5', 1.8, 0.50),
        (1, 0.0, 'G5', 0.9, 0.48), (1, 1.0, 'E5', 0.8, 0.45), (1, 2.0, 'D5', 1.8, 0.45),
        (2, 0.0, 'B4', 0.8, 0.44), (2, 1.0, 'C5', 0.8, 0.45), (2, 2.0, 'D5', 1.8, 0.48),
        (3, 0.0, 'C5', 0.8, 0.46), (3, 1.0, 'B4', 0.8, 0.44), (3, 2.0, 'A4', 2.0, 0.48),

        # Bメロ
        (4, 0.0, 'A4', 0.8, 0.45), (4, 1.0, 'C5', 0.8, 0.46), (4, 2.0, 'E5', 0.8, 0.48), (4, 3.0, 'G5', 1.0, 0.50),
        (5, 0.0, 'F5', 1.0, 0.48), (5, 1.0, 'E5', 0.8, 0.46), (5, 2.0, 'D5', 1.8, 0.48),
        (6, 0.0, 'G5', 0.8, 0.50), (6, 1.0, 'E5', 0.8, 0.46), (6, 2.0, 'B4', 1.8, 0.44),
        (7, 0.0, 'C5', 0.8, 0.46), (7, 1.0, 'D5', 0.8, 0.48), (7, 2.0, 'E5', 1.8, 0.52),

        # サビ
        (8, 0.0, 'A5', 1.2, 0.55), (8, 1.5, 'G5', 0.8, 0.50), (8, 2.5, 'E5', 1.5, 0.52),
        (9, 0.0, 'G5', 1.0, 0.52), (9, 1.0, 'E5', 0.8, 0.48), (9, 2.0, 'D5', 1.8, 0.50),
        (10, 0.0, 'G5', 1.0, 0.50), (10, 1.0, 'D5', 0.8, 0.48), (10, 2.0, 'C5', 1.8, 0.48),
        (11, 0.0, 'E5', 0.8, 0.48), (11, 1.0, 'D5', 0.8, 0.46), (11, 2.0, 'C5', 0.8, 0.46), (11, 3.0, 'A4', 1.0, 0.46),

        # フィナーレ展開
        (12, 0.0, 'F4', 0.8, 0.45), (12, 1.0, 'A4', 0.8, 0.46), (12, 2.0, 'C5', 0.8, 0.48), (12, 3.0, 'D5', 1.0, 0.50),
        (13, 0.0, 'E5', 0.8, 0.50), (13, 1.0, 'F5', 0.8, 0.50), (13, 2.0, 'G5', 1.0, 0.54), (13, 3.0, 'B4', 1.0, 0.48),
    ]

    for m_bar, b_offset, n_str, dur_beats, vol in melody:
        t_note = m_bar * (4 * beat) + b_offset * beat
        midi = note_to_midi(n_str)
        dur_sec = dur_beats * beat

        p_s = sampler.get_sample('piano', midi)
        add_to_track(track_melody, p_s, t_note, volume=vol * 0.75, pan=-0.05, max_dur=dur_sec)

        x_s = sampler.get_sample('xylophone', midi)
        add_to_track(track_melody, x_s, t_note, volume=vol * 0.42, pan=0.12, max_dur=dur_sec * 0.75)

    # 3. 28.96秒 解決エンドジングル (Cmaj9)
    t_end = 14 * (4 * beat)
    cadence_chord = [
        note_to_midi('C2'), note_to_midi('G2'), note_to_midi('C3'), note_to_midi('E3'),
        note_to_midi('G3'), note_to_midi('B3'), note_to_midi('D4'), note_to_midi('E4'), note_to_midi('G4'),
    ]

    add_to_track(track_drums, sampler.samples['kick'], t_end, volume=0.55, pan=-0.05)
    add_to_track(track_drums, sampler.samples['snare'], t_end, volume=0.40, pan=0.05)

    for i, cm_midi in enumerate(cadence_chord):
        p_s = sampler.get_sample('piano', cm_midi)
        pan_c = -0.3 + 0.6 * (i / (len(cadence_chord) - 1))
        # 和音も20msずつアルペジオ
        add_to_track(track_harmony, p_s, t_end + i * 0.018, volume=0.45, pan=pan_c, max_dur=1.03)
        if i >= 4:
            x_s = sampler.get_sample('xylophone', cm_midi)
            add_to_track(track_harmony, x_s, t_end + i * 0.018, volume=0.32, pan=pan_c, max_dur=0.9)

    # ========================================================
    # 4. ★Claude流 高度DSPマスタリングパイプライン★
    # ========================================================
    print("Applying Claude-style DSP Effects (Reverb, Delay, Warmth, Ducking)...")

    # 4-1. アナログ・ウォームフィルター（キンキン感をカットし、丸いLo-Fiトーンへ）
    track_harmony = apply_warm_lowpass(track_harmony, alpha=0.30)
    track_melody = apply_warm_lowpass(track_melody, alpha=0.20)

    # 4-2. ピンポン・ステレオディレイ（メロディに爽快な浮遊感を付与）
    track_melody = apply_pingpong_delay(track_melody, sr=sr, delay_l_sec=0.258, delay_r_sec=0.387, feedback=0.25, wet=0.18)

    # 4-3. FFTコンボリューション・スタジオプレートリバーブ（伴奏＋メロディに豊かな空間を付与）
    harmony_and_melody = track_harmony + track_melody
    wet_harmony_melody = apply_fft_reverb(harmony_and_melody, sr=sr, rt60=1.4, wet_gain=0.22)

    # 4-4. キック連動サイドチェーン・ダッキング（ビートに合わせた心地よいグルーヴ）
    # ドラムのキック位置を検出し、その瞬間の伴奏音量を一瞬だけ 18% ダッキング
    kick_positions = []
    for bar in range(total_bars):
        t_b = bar * (4 * beat)
        kick_positions.extend([t_b, t_b + 2 * beat])
    kick_positions.append(t_end)

    ducking_envelope = np.ones((total_samples, 1), dtype=np.float32)
    duck_len = int(0.09 * sr) # 90ms
    duck_curve = 1.0 - 0.20 * np.sin(np.linspace(0, np.pi, duck_len))[:, None]

    for kp in kick_positions:
        k_idx = int(kp * sr)
        if k_idx + duck_len < total_samples:
            ducking_envelope[k_idx:k_idx + duck_len] *= duck_curve

    ducked_harmony_melody = wet_harmony_melody * ducking_envelope

    # 4-5. トラック全合成（ベースとドラムはクリアさを維持するためドライ寄り＋リバーブ微量）
    final_mix = ducked_harmony_melody + track_bass * 0.95 + track_drums

    # 4-6. ノーマライズ＆末尾フェードアウト
    max_val = np.max(np.abs(final_mix))
    if max_val > 0:
        final_mix = (final_mix / max_val) * 0.88

    fade_len = int(0.15 * sr)
    fade_curve = np.linspace(1.0, 0.0, fade_len)[:, None]
    final_mix[-fade_len:] *= fade_curve

    # 16-bit PCM WAV書き出し
    mix_16 = (final_mix * 32767).astype(np.int16)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(mix_16.tobytes())

    print(f"Mastered Studio Lo-Fi BGM generated successfully -> {output_path}")

if __name__ == "__main__":
    out_file = Path("public/audio/bgm_dynamic_30s.wav")
    compose_advanced_claude_style_bgm(out_file)
