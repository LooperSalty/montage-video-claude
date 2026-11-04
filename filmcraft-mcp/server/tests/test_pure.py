"""Tests des fonctions pures du MCP compagnon (sans ffmpeg, GPU ni FilmCraft)."""

from fractions import Fraction
from pathlib import Path

from filmcraft_assist import beats, config, media, qc, sheet, transcribe
from filmcraft_assist.bridge import same_path
from filmcraft_assist.transcribe import Word


def test_ticks_roundtrip():
    assert config.seconds_to_ticks(1) == 254_016_000_000
    assert config.seconds_to_ticks(1001 / 30000) == 8_475_667_200  # une image à 29,97 exacte
    assert config.ticks_to_seconds(config.seconds_to_ticks(12.5)) == 12.5


def test_vfr_detection():
    assert not media.is_probably_vfr(Fraction(30000, 1001), Fraction(30000, 1001))
    assert media.is_probably_vfr(Fraction(30), Fraction(1800000, 60061))
    assert not media.is_probably_vfr(None, Fraction(30))
    assert media.nearest_standard_rate(Fraction(1800000, 60061)) == Fraction(30000, 1001)
    assert media.parse_rate("0/0") is None and media.parse_rate("25/1") == 25


def test_summarize_flags_phone_footage():
    data = {"format": {"format_name": "mov", "duration": "10.0", "size": "1000", "bit_rate": "800"},
            "streams": [
                {"codec_type": "video", "codec_name": "hevc", "width": 1920, "height": 1080,
                 "r_frame_rate": "30/1", "avg_frame_rate": "1800000/60061", "color_transfer": "arib-std-b67",
                 "side_data_list": [{"rotation": -90}]},
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "44100", "channels": 2}]}
    s = media.summarize(Path("C:/x.mov"), data)
    assert s["video"]["probablyVFR"] and s["video"]["hdr"] == "HLG" and s["video"]["rotation"] == -90
    assert len(s["issues"]) == 4


def test_cues_break_on_sentence_gap_and_length():
    words = [Word("Bonjour", 0.0, 0.4, 1), Word("à", 0.45, 0.5, 1), Word("tous.", 0.55, 0.9, 1),
             Word("On", 2.0, 2.1, 1), Word("commence", 2.15, 2.6, 1)]
    cues = transcribe.build_cues(words, max_chars=42, max_lines=2, max_seconds=6, max_gap=0.6)
    assert [c[2] for c in cues] == ["Bonjour à tous.", "On commence"]
    long_words = [Word(f"mot{i}", i * 0.3, i * 0.3 + 0.2, 1) for i in range(20)]
    for _, _, text in transcribe.build_cues(long_words, 20, 2, 60, 1.0):
        assert all(len(line) <= 20 for line in text.split("\n"))


def test_srt_format():
    srt = transcribe.to_srt([(0.0, 1.5, "Salut"), (3661.25, 3662.0, "a\nb")])
    assert "1\n00:00:00,000 --> 00:00:01,500\nSalut\n" in srt
    assert "2\n01:01:01,250 --> 01:01:02,000\na\nb\n" in srt


def test_filmcraft_transcript_has_no_overlap():
    words = [Word("a", 0.0, 1.2, 0.9), Word("b", 1.0, 2.0, 1.5)]
    t = transcribe.to_filmcraft(words, "fr", "large-v3-turbo")
    assert t["words"][0]["end"] == t["words"][1]["start"] == config.seconds_to_ticks(1.0)
    assert t["words"][1]["confidence"] == 1.0 and t["source"] == "faster-whisper-large-v3-turbo"


def test_merge_split_words():
    words = [Word("aujourd", 0.0, 0.3, 0.9), Word("'hui", 0.3, 0.5, 0.8), Word("c", 1.0, 1.1, 1),
             Word("'est", 1.1, 1.3, 1), Word("sous", 2.0, 2.2, 1), Word("-titres", 2.2, 2.6, 1),
             Word("-", 3.0, 3.1, 1)]
    merged = transcribe.merge_split_words(words)
    assert [w.text for w in merged] == ["aujourd'hui", "c'est", "sous-titres", "-"]
    assert merged[0].start == 0.0 and merged[0].end == 0.5 and merged[0].probability == 0.8


def test_count_fillers():
    words = [Word("Euh,", 0, 1, 1), Word("bon", 1, 2, 1), Word("euh...", 2, 3, 1), Word("hum", 3, 4, 1)]
    assert transcribe.count_fillers(words, "fr") == {"euh": 2, "hum": 1}


def test_downbeat_and_selection():
    strengths = [1, 1, 5, 1, 1, 1, 6, 1, 1, 1, 5, 1]
    assert beats.downbeat_phase(strengths) == 2
    times = [float(i) for i in range(12)]
    assert beats.select_times(times, 2, "bar") == [2.0, 6.0, 10.0]
    assert beats.select_times(times, 2, "half_bar") == [2.0, 4.0, 6.0, 8.0, 10.0]


SAMPLE_STDERR = """
[blackdetect @ 0x1] black_start:0 black_end:0.5 black_duration:0.5
[blackdetect @ 0x1] black_start:12.04 black_end:13.1 black_duration:1.06
[freezedetect @ 0x2] lavfi.freezedetect.freeze_start: 20.5
[freezedetect @ 0x2] lavfi.freezedetect.freeze_duration: 3
[freezedetect @ 0x2] lavfi.freezedetect.freeze_end: 23.5
[silencedetect @ 0x3] silence_start: 40.2
[silencedetect @ 0x3] silence_end: 43.0 | silence_duration: 2.8
[Parsed_ebur128_0 @ 0x4] Summary:

  Integrated loudness:
    I:         -18.3 LUFS
    Threshold: -28.5 LUFS

  Loudness range:
    LRA:         6.1 LU

  True peak:
    Peak:       -0.4 dBFS
"""


def test_qc_parse_and_evaluate():
    report = qc.parse_report(SAMPLE_STDERR, duration=60.0)
    assert report["integratedLufs"] == -18.3 and report["truePeakDbtp"] == -0.4
    assert report["black"] == [[0.0, 0.5], [12.04, 13.1]]
    assert report["frozen"] == [[20.5, 23.5]] and report["silence"] == [[40.2, 43.0]]
    checks = {c["check"]: c for c in qc.evaluate(report, "youtube", 60.0)}
    assert checks["loudness"]["status"] == "à corriger" and "loudnessLufs=-14" in checks["loudness"]["fix"]
    assert checks["true peak"]["status"] == "à corriger"
    assert "1 passage" in checks["noirs"]["detail"]  # le noir d'ouverture est ignoré


def test_sheet_times_and_timecode():
    assert sheet.sample_times(10, 4) == [1.25, 3.75, 6.25, 8.75]
    assert sheet.sample_times(10, 2, start=4, end=8) == [5.0, 7.0]
    assert sheet.sample_times(0, 4) == []
    assert sheet.timecode(65.5) == "01:05.50" and sheet.timecode(3725) == "1:02:05.00"


def test_blacks_at_edges_only_ignored_when_fade_length():
    duration = 60.0
    blacks = [[0.0, 0.5], [12.0, 13.0], [50.0, 60.0], [0.0, 30.0], [59.2, 60.0]]
    assert qc.suspicious_blacks(blacks, duration) == [[12.0, 13.0], [50.0, 60.0], [0.0, 30.0]]


def test_conform_target_rate_is_exact_ntsc():
    assert media.target_rate(29.97, None) == Fraction(30000, 1001)
    assert media.target_rate(23.976, None) == Fraction(24000, 1001)
    assert media.target_rate(59.94, None) == Fraction(60000, 1001)
    assert media.target_rate(12.5, None) == Fraction(25, 2)
    assert media.target_rate(None, Fraction(1800000, 60061)) == Fraction(30000, 1001)


def test_media_duration_falls_back_to_streams():
    assert sheet.media_duration({"format": {"duration": "12.5"}}) == 12.5
    assert sheet.media_duration({"format": {}, "streams": [{"duration": "3.0"}, {"duration": "4.2"}]}) == 4.2
    assert sheet.media_duration({}) == 0.0


def test_worker_result_survives_cp1252_pipe():
    from filmcraft_assist.worker import encode_result
    import json

    raw = encode_result({"words": [["à", 0, 1, 1], ["vidéo", 1, 2, 1], ["c'est", 2, 3, 1]]})
    assert raw.decode("cp1252") == raw.decode("ascii")  # aucun octet non ASCII
    assert json.loads(raw)["words"][1][0] == "vidéo"


def test_same_path_is_case_and_slash_insensitive():
    assert same_path("C:/Videos/Rush.MP4", r"c:\videos\rush.mp4")
    assert not same_path(None, "C:/a.mp4")
