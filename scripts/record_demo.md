# Recording the TerraLens Demo GIF

Target: 8-10 second loop, < 5MB, autoplay in GitHub markdown.

## Tools

**Windows (recommended):** [ScreenToGif](https://www.screentogif.com/) — free, captures region, exports optimized GIF.

**Alternative:** OBS Studio → MP4 → [ezgif.com](https://ezgif.com/video-to-gif) converter.

## Steps

1. Open https://terra-lens-zeta.vercel.app in Chrome at **1280×720** window (devtools → no device emulation)
2. Wait for preloader to finish
3. Open ScreenToGif → Recorder → select the globe area (full window or cropped to globe)
4. Set **15 fps** (matches mobile throttle, smaller file)
5. Click Record
6. Watch the full automatic tour: globe → Amazonia → Dubai → Arctic → heatmap reveal
7. Stop after Arctic heatmap is visible (≈8-10s)
8. In ScreenToGif editor: File → Save As → GIF
   - Quality: 70%
   - Max colors: 128
   - Target < 5MB — if larger, reduce to 720×405 or cut to 8s

## Placement in README

Add after the badges, before the Live Demo link:

```markdown
![TerraLens demo](docs/terralens_demo.gif)
```

Save the file as `docs/terralens_demo.gif`.

## Screenshot (static fallback)

For the GitHub social preview (`Settings → Social preview`):
1. Pause the tour over Amazonia with heatmap visible
2. Screenshot at 1280×640
3. Save as `docs/terralens_screenshot.png`
4. Upload in GitHub repo Settings → Social preview

## Tips

- Record in incognito to avoid extension interference
- If the tour auto-plays too fast, reload and start recording immediately
- The preloader takes 2-3s — you can trim it in ScreenToGif editor
