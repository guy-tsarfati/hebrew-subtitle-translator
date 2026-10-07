# Changelog

Release dates and tags are recorded when published. The first preview release is being prepared.

## Unreleased

Changes after the first preview will be listed here.

## 0.1.0 preview

First public preview. See the release page for publication status and date.

### Existing public baseline

- English-to-Hebrew SRT skill for translation, repair, and selective polishing.
- Preparation, validation, build, audit, and bilingual editorial-review helpers.
- Guidance for source-bound SDH/credit cleanup, gender consistency, and RTL output.
- Synthetic pipeline and quality checks in GitHub Actions.
- CueIvrit branding, Wiki, contributor guide, security policy, issue forms, and PR template.
- A 26-cue Sintel worked example with separate Creative Commons attribution.
- Code of Conduct with private reporting to guy@tsarfati.com.

### Added on 2026-10-05

- Support routes and a checklist for useful feedback in SUPPORT.md.
- A public roadmap and launch tracking issue.

### Added on 2026-10-07

- Verified project installation through skills CLI 1.7.1 for the Codex target, with all bundled resources checked.
- Installation guide, first-release verification report, and a trial feedback issue form.
- CI rebuild and audit of the licensed Sintel example, including byte equality with the committed Hebrew SRT.

### Preview preparation on 2026-10-07

- Documented Node.js 22.20.0+ as the tested installer requirement.
- Visually inspected all 26 Hebrew cues on rendered Sintel film frames with FFmpeg/libass.
- Prepared v0.1.0 preview release notes with explicit rendering and assistant-test limitations.

### Pending release checks

- Versioned release archive verification is recorded on the release page after publication.
- Native player playback remains unverified. Rendered-frame validation with FFmpeg/libass is documented in VISUAL_CHECK.md.

The structural tests and audit do not certify semantic translation quality or universal player compatibility.
