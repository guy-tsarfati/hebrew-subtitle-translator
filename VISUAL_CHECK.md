# Sintel visual rendering check

Checked on 2026-10-07 using FFmpeg 6.1.1 with libass on Linux. This is a rendered-frame check, not a complete playback test in VLC, Plex, or a browser's native subtitle engine.

## Inputs and method

- Film: the 1280x544, 24 fps Sintel MKV from the [official Blender download directory](https://download.blender.org/demo/movies/Sintel.2010.720p.mkv.zip), linked by the [project download page](https://durian.blender.org/download/).
- Film SHA-256 after extraction: `60cff51761641626e82eeb4e1c248c471375b2536bb1089f49825b7fb58d8723`.
- Subtitles: the unmodified [examples/sintel.he.srt](examples/sintel.he.srt), SHA-256 `72e9ac916ad836d14f9c18d55c62dc36e5f9f7e911ee872034bc57febe646c51`.
- One actual film frame was rendered at the midpoint of each of the 26 subtitle intervals, using the external Hebrew SRT and its existing RTL controls. All 26 frames were visually inspected.
- Font/style: DejaVu Sans, size 24, outline 2, vertical margin 24 in libass. Changing font, window size, or renderer can change the result.

An example command for cue 3 is:

```bash
ffmpeg -ss 119.725 -i Sintel.2010.720p.mkv -map 0:v:0 -frames:v 1 \
  -vf "setpts=PTS+119.725/TB,subtitles=examples/sintel.he.srt:force_style='FontName=DejaVu Sans,FontSize=24,Outline=2,MarginV=24'" \
  cue-03.png
```

`setpts` restores the film time after seeking so the subtitle filter selects the original cue. This command creates a QA frame, not an automatically retimed SRT.

## Observed result

Hebrew word order, terminal punctuation, question marks, exclamation marks, ellipses, and the two-line cue 3 displayed legibly. No clipped text or missing Hebrew glyphs were visible in these 26 frames. This sample contains no mixed Hebrew/Latin dialogue and no SDH or subtitle credits, so those cases were not visually exercised.

All 26 cue start times match the film's embedded English subtitle track. Cue 1 ends at `00:01:50,500` in the Commons-derived example and `00:01:49,220` in the embedded track. All other end times match. The example preserves its own authoritative English source timing. The check did not change either SRT or certify audiovisual synchronization from still frames.

## Scope and attribution

This result supports rendering with the tested FFmpeg/libass configuration only. Native player playback, mixed Hebrew/Latin text, other fonts, operating systems, and player versions remain open tests. Structural audits and these frames do not certify all translation choices.

Film frames: (c) Blender Foundation, durian.blender.org, CC BY 3.0. The Hebrew adaptation retains its CC BY-SA 4.0 terms and attribution in [examples/README.md](examples/README.md). Any distributed contact sheets are annotated derivative QA images shared under CC BY-SA 4.0, with attribution. The full film is not included in CueIvrit's release archive.
