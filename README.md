# Tristan Buckmaster’s academic website

The site uses Jekyll and Jekyll-Scholar. It builds static HTML for the homepage, Publications, Media, Videos, CV, and Misc. The homepage includes the students and postdocs roster at `/#people`. The former `/people/` page redirects there, and `/talks/` redirects to `/videos/`.

## Preview and build

Use Ruby 3.1.2 (see `.ruby-version`) and run these commands from the repository root. The lockfile pins the gems for macOS and Linux.

```sh
gem install bundler -v 2.3.7
BUNDLE_FROZEN=true bundle _2.3.7_ install
bundle exec jekyll serve --baseurl ""
```

Open the local URL printed by Jekyll. A standard build uses the configured Courant path, `/~tristanb`.

```sh
bundle exec jekyll build
```

## Publish to Courant

Run `./deploy.sh --dry-run` to compare a fresh build with the Courant web directory over SSH. It lists pending changes. When ready to publish, run `./deploy.sh --apply`. The upload overlays built files and leaves server-only documents in place, including those in subdirectories. It explicitly protects the root `statement.pdf` and server `.htaccess` files. To retire a URL, remove its remote file separately.

Run `bin/test-courant-upload` to exercise the uploader against a temporary local directory.

## Add or update content

| Content | Source | How to update it |
| --- | --- | --- |
| Publications | `_bibliography/papers.bib` | Edit this shared bibliography once, then run `bin/build-cv` to refresh the PDF. Publications groups entries by year. For a manuscript hosted outside arXiv, use its actual `url` or `pdf` and an optional `link_label`. |
| Slop mark | `_data/slop_papers.yml` | Add or remove a paper’s BibTeX key. For a research highlight or news entry featuring that paper, set its `paper_key` to the same key. The ink mark links to the symbol key on Publications. |
| Videos | `_data/talks.json` | Add a dated record with a title, venue, and recording URL. A YouTube ID enables playback on the page. An event URL, local poster, and description are optional. |
| Media | `_data/media.json` | Add a date, title, outlet, format (`type`), publisher URL and audience (`group`, either `popular-science` or `general-media`). Add an author or interviewer when credited. An optional description can distinguish an interview from reporting. Use `links` for companion media. Add `youtube_id` and a local `poster` path to a recording link for an inline player. An optional entry `id` gives it a direct link on the Media page. |
| CV | `assets/pdf/CV.tex`, `_data/cv_overview.json` | Edit the LaTeX for the full CV or the overview for the short HTML version. Rebuild the PDF after changing the LaTeX or shared bibliography. |
| Research highlights | `_data/highlights.yml`, `assets/figures/` | Add a record with a unique ID, tab label, summary, paper link, figure, dimensions, alt text, caption, and source link. For one movie, set `movie` to the MP4 and `figure` to its poster. For matched movies, add a `clips` list with a label, MP4 path (`movie`), poster, description, and caption for each. Give the clips a common timeline so the player can switch at the same instant. |
| What’s new | `_data/updates.yml`, `_data/media.json` | Add a `date`, `kind`, `title`, `url`, and optional `note` for an announcement. To feature an existing Media item, set `"in_news": true` on its record. The homepage sorts both by date. |
| Profile and funding | `_data/profile.yml`, `_pages/about.md` | Update contact information, affiliation, portrait, or award links in the data file. The opening and acknowledgment are arranged in the homepage template. |
| Navigation | `_data/navigation.yml` | Add or reorder a page title and site-relative path. The layout applies the site’s base URL. |
| Students and postdocs | `_data/people.yml` | Add a student or postdoc to the appropriate group, or move their entry when they leave. The homepage disclosure uses this list. |
| Misc | `_data/misc.yml` | Add a titled link and description to a section. An item can reuse a homepage update’s title and URL by referencing its `id` in `update`. |

Page templates live in `_pages/`. The shared layout is `_layouts/plates.html`, and the shared header, footer, and research feature are in `_includes/plates/`. Page-specific styles and scripts are loaded through the `page_css` and `page_js` front matter fields. Publications and all research topics remain readable with JavaScript disabled.

## Review the media archive

Open `/media/review/` on the local preview. Check **Keep** beside each link you want to retain, including any companion recordings. The page saves your draft in the current browser. **Export decisions** downloads `media-review.json`, marking unchecked links for removal.

Preview what the file would change from the repository root:

```sh
python3 bin/apply-media-review.py ~/Downloads/media-review.json
```

Add `--apply` to write those changes to `_data/media.json`. Links added after the review are preserved. If you keep only a companion link, it becomes the primary link for that entry.

## Build the CV

Run the commands below from the repository root. Building the PDF requires Python 3, `latexmk`, pdfLaTeX, BibLaTeX, Biber, and the TeX Live font packages `stix2-type1` and `sourcesanspro`. The build uses a clean directory and refreshes `assets/pdf/CV.pdf`. The downloadable `assets/pdf/papers.bib` points to the same bibliography used by Publications.

```sh
bin/build-cv
bin/build-cv --check
```

Commit the rebuilt PDF with any change to the bibliography or CV source. The check only needs Python 3. It verifies the source fingerprints embedded in the PDF and also runs before a Courant upload.

## Research figures

- **Singularity formation.** Figure 1 on page 4 of Levent Alpöge and Tristan Buckmaster’s *Finite-time blow-up for the Navier–Stokes equations*. The image is the original two-panel figure, encoded losslessly as WebP. It shows the computed approximate profile at two vorticity magnitudes. [Pinned manuscript](https://github.com/tristanbuckmaster/navier-stokes/blob/b86ec358087c6d32c4bff73f4ef440f7491b426f/paper/finite-time-blow-up-navier-stokes.pdf)
- **Non-uniqueness.** Two streamfunction animations use the same uniformly spaced planar row of Gaussian vortices. The symmetric reference repeats a freely diffusing radial Gaussian. The second repeats that core with its linearized angular-two perturbation. Both use the paper’s logarithmic ring coordinates and the same physical times. The paper treats interactions between cores and constructs a Floquet mode for the full three-dimensional flow. [Periodic train, §3](https://hexagonmath.org/pdf/2611.00143v1#page=8) · [Gaussian instability, §4](https://hexagonmath.org/pdf/2611.00143v1#page=12) · [Ring coordinates, §5](https://hexagonmath.org/pdf/2611.00143v1#page=19)
- **Wave turbulence.** The two Feynman trees in `assets/figures/wave-interaction-diagrams.svg` represent the cubic term in equation (3.2b) and the third-order term in Figure 1. Each vertex has the momentum rule `k = k₁ − k₂ + k₃`. Dashed branches denote conjugated factors. [Figure 1 and equation (4.2)](https://arxiv.org/pdf/1907.03667#page=12)

### Reproduce the viscous vortex-train comparison

In each frame the centers repeat at `q = nc` in the planar coordinate, for integer `n`. In the radial coordinate their initial positions are `rₙ = R exp(nc/R)`. This geometric sequence places progressively smaller, more closely spaced rings near the axis. At physical time `t`, each radius samples the core evolution at the local age `s = R²t/r²`. The symmetric reference stays mirror-symmetric across `z = 0` as its outer contours join.

For the second view, `bin/vortex_eigenmode.py` computes the Gaussian’s angular-two vorticity eigenfunction and eigenvalue `λ ≈ 0.0222674 − 0.2696523i`. The generator evolves a small multiple of that mode using the viscous equation linearized around the diffusing core, then repeats the resulting streamfunction at the same planar centers. The tilt changes the shape of the contours while preserving the train’s periodic placement. Both views use fixed levels of the normalized meridional streamfunction `S = −rψ/(2R)`. Both use the same contour colors on a flat background. The amber contours mark `S = 0.046, 0.235, 0.63`. The dashed line marks `z = 0` so readers can compare the upper and lower arcs at a common time. The movies use `c = 8`, `R = 35`, viscosity `ν = 0.009`, and physical times `t = 0.05` to `170`. In the perturbed view the seed has amplitude `0.09` for a unit-peak complex vorticity mode and phase `π/2`.

The generator requires NumPy, SciPy, and Pillow 10.1 or newer. The macOS encoder uses AVFoundation.

```sh
python3 bin/generate-vortex-movies.py /tmp/ring-lift --validate
swiftc bin/encode-figure-frames.swift -o /tmp/encode-figure-frames
/tmp/encode-figure-frames /tmp/ring-lift/reference/frames /tmp/ring-lift/viscous-ring-lift.mp4 20
/tmp/encode-figure-frames /tmp/ring-lift/perturbed/frames /tmp/ring-lift/viscous-ring-mode.mp4 20
```

Copy the two MP4s and their `viscous-ring-*-poster.webp` files from `/tmp/ring-lift/` into `assets/figures/`. The checked-in videos play offline.
