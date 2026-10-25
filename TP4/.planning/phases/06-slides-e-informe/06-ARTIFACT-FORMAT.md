---
probed_at: 2026-10-25T22:10:00Z
slides_type_available: true
content_unit: one slide = project/slides/<id>.html holding exactly one <section id="<id>">; order given by the order list in project/deck.json (v4 index)
canvas: 1920x1080 px fixed (1664x824 inside the 128 px margins)
figure_area: about 1664x630 px below a 72 px h2 title with a 32 px gap (about 2.6:1); two side-by-side figures get about 816x454 each
image_embed: relative-file
notes_supported: true
notes_field: plain text in one <aside> as the last child of the slide's <section>, max 4000 characters, visible to anyone who opens the deck
export_formats: PDF (verified by the user), PPTX and web page (listed by the type docs, not exported in the probe)
export_keeps_images: true
redeploy_same_url: true
default_visibility: private (readable only by the owner until shared from the Share menu)
share_mode: PDF export of the deck submitted to the teacher; no share link required
smoke_deck_url: https://claude.ai/artifact/3J6BXCDx8XMprfLBKE5Y3s
---

# Slides Artifact format (probe of 2026-10-25)

Probe done by the top-level session with the Artifact tool (`quickstart` intent "slides", then a
2-slide smoke deck "Prueba de formato TP4" created from the core "Slides" type, release
1792801637-7984, contract 0.2.47). Visual answers come from the user looking at the published deck.
No design system is attached to this account, so the deck uses its own palette and one Google font.

## 1. Content contract

- A deck is the artifact's own files under `project/`:
  - `project/deck.json`: `{"v":4, "createdOnFiles":{"v":1,"at":"<RFC 3339>"}, "lists":"css", "title", "cover", "order":[slide ids], "sections":{key:{"description","start"}}, "faces":{family-id:{"family","href"}}, "designSystems":[]}`.
  - `project/slides/<id>.html`: exactly one `<section id="<id>" style="…">`, nothing before or after it. The file name equals the section id; ids match `[A-Za-z0-9_-]{1,64}`.
- `order` places the slides. A slide file missing from `order` is shown last.
- Styles are inline only, from a closed CSS subset (px lengths, hex/rgb colors; no classes, `<style>`, `margin`, `z-index`, `em`, `var()`). Allowed elements: h1-h3, p, ul/ol/li, div, img, table, inline svg (52 KB max), hr, x-shape, x-icon, x-connector, x-embed. At most 200 elements per slide.
- Typefaces: up to 4, declared in `faces` with a `https://fonts.googleapis.com/css2?…` href (or an uploaded font). Basic faces (Arial, Georgia…) need no entry.
- For 06-10: `analysis/slides.py` should emit exactly this tree (deck.json + one html per slide) into a local folder that is then published as the artifact's `root`.

## 2. Canvas and type scale

- Fixed 1920x1080 px canvas. The usual section padding is 128 px, which leaves 1664x824 px. A footer row (page number or source) is one pinned 24 px line at `bottom:64px`, with padding `128px 128px 160px` on that slide.
- Minimum font size is 24 px everywhere, footers and table cells included. Tag defaults are h1 96, h2 64, h3 44, p 32 px.
- Scale used in the probe, and suggested for the real deck: 120 (cover title), 72 (slide title), 44, 32, 24.
- Text wraps only at spaces. Size each box to its longest word, at about 0.6 x font-size per character.

## 3. Image embedding

Two modes were tried on slide 2 with `analysis/results/som/figures/map.svg` (4 embedded raster `<image>` cells):

- **data: URI (`data:image/svg+xml;base64,…`)**: not tried, because the type forbids it. Its instructions and `images.md` say "never a `data:` URI, other path or http(s) URL" in `<img src>`. Only `/_blob/<id>` (an uploaded asset) or `project/ds/<folder>/…` (a design-system file) are accepted.
- **SVG uploaded as an asset (`/_blob/<id>`)**: the upload worked (106175 to 100672 bytes). The store kept the 4 `<image>` tags but removed every embedded `data:image` payload and the `<style>` block. Read back from the store: `<image>` count 4, `data:image` count 0, `<style>` count 0. **The user saw the map striped, not colored**: the raster cells are lost.
- **PNG uploaded as an asset (`/_blob/<id>`)**: `map.png` (1725x960) uploaded unchanged. The user could see the difference between the two images, and the PNG shows the map correctly.

Contract for 06-05 and 06-10:
- Every slide figure is a **PNG** uploaded as an asset. Its `src` is the returned `/_blob/<id>`, written verbatim.
- Never use an SVG that contains raster `<image>` elements. matplotlib heatmaps and imshow output embed such rasters, so the store strips them.
- A pure-vector SVG would survive, but PNG is the single rule.
- Render slide PNGs at about 2x their box: a full-width figure at about 3300x1260 px, a half-width one at about 1630x910 px.
- Use `object-fit:contain` on a contrasting background.
- Labels stay inside the PNG, since matplotlib draws them. Fonts never load inside an SVG anyway.

## 4. Speaker notes

- Supported: plain text in one `<aside>`, the last child of the `<section>`, up to 4000 characters.
- **The notes are not presenter-only.** The type's docs say "anyone who opens the deck can read them", and the user saw the slide 2 note on the normal deck page.
- With `share_mode` = PDF submission, the PDF export is the deliverable. The probe did not check whether the PDF includes the notes.
- So that the spoken script still reaches the teacher, keep the D-06 fallback as well as the `<aside>` notes:
  - `analysis/results/slides/notes.md`, generated from the same outline;
  - an informe annex "Guion de la presentación".
- This is a recommendation for 06-09/06-10, not a forced fallback, since `notes_supported` is true.
- Notes must not contain anything that shouldn't be read by whoever opens the deck.

## 5. Local build then publish from files

1. `analysis/slides.py` writes `project/deck.json` and `project/slides/<id>.html` under one local folder (the publish `root`), plus the slide PNGs.
2. The top-level session uploads the PNGs as assets with Artifact `publish`, `asset: true` and `file_paths` (up to 25 per call). It then writes each returned `/_blob/<id>` into the slides' `<img src>`. Option: the build reads a small `asset_map.json` of PNG name to blob url, so the html is generated with final srcs.
3. Then one publish with `url` = the deck, `root` = the folder, `file_path` = `<root>/project/deck.json` and `files` = the slide files. Later updates send only the changed files. Send `deck.json` only when order, title, sections or faces change.
4. Never publish `index.html`, `SKILL.md` or anything under `artifact-type/`. Those belong to the type.
5. Executors have no Artifact tool, so every upload and publish is a top-level session step.

## 6. Redeploy and URL

- Publishing again to the same `url` updated the deck in place. Version 1 was the empty create and version 2 the 2-slide publish, both at the same URL.
- `redeploy_same_url` is true. The final deck should be built as new versions of one artifact. Do not create a second deck.
- Uploaded assets persist across versions until deleted. A changed PNG needs a new upload, which gives a new `/_blob/<id>`, and the slide referencing it has to be republished.

## 7. Export to PDF/.pptx

- **PDF:** verified by the user ("PDF extraction is perfect"). The PNG figure and the layout come through.
- **PPTX** and the web page are listed in the type's docs (Share > Export). They were not exported in this probe.
  - A PPTX export names the linked Google font, or carries it where the type allows. A machine without the font substitutes it.
  - A "slides as pictures" PPTX needs no fonts.
  - Plain SVGs are rasterized to PNG for PPTX.
- The deliverable is the PDF, so PPTX fidelity is not on the critical path.

## 8. Visibility and sharing

- Default visibility is private: "readable by only you". The probe deck stays private (T-06-04).
- Sharing can only be changed by the user from the page's Share menu. The tool cannot change it.
- `share_mode` (user's answer, 2026-10-25): **"we will submit the presentations PDF"**. The teacher gets the exported PDF, so the deck itself never needs to be shared. 06-11/06-12 should add the exported PDF to the deliverables, with its path under `deliverables/`, and keep the artifact private.
