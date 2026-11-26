# Tristan Buckmaster’s academic website

The site uses Jekyll and Jekyll-Scholar. It builds static HTML for the homepage, Publications, Media, Talks, and CV. Every page uses the same navigation, footer, and type styles.

## Preview and build

Use the repository’s Ruby environment and run the commands from its root.

```sh
bundle install
bundle exec jekyll serve --baseurl ""
```

Open the local URL printed by Jekyll. A standard build uses the configured Courant path, `/~tristanb`.

```sh
bundle exec jekyll build
```

The Courant web directory also holds public documents outside this repository, including `statement.pdf`. The legacy `deploy.sh` calls `server.sh`, which clears that directory before it uploads the build. A future Courant deployment should preserve those files and their existing URLs.

## Add or update content

| Content | Source | How to update it |
| --- | --- | --- |
| Publications | `_bibliography/papers.bib` | Add a BibTeX record with a unique key, title, authors, and year. The bibliography groups years automatically. Optional fields include abstract, DOI, arXiv, URL, PDF, and code. |
| Slop mark | `_data/slop_papers.yml` | Add or remove a paper’s BibTeX key. For a research highlight or news entry featuring that paper, set its `paper_key` to the same key. The ink mark links to the symbol key on Publications. |
| Talks | `_data/talks.json` | Add a dated record with a title, venue, and recording URL. A YouTube ID enables playback on the page. An event URL, local poster, and description are optional. |
| Media | `_data/media.json` | Add the publication date, headline, author, outlet, type, and article URL. Use the outlet name “Quanta Magazine” for Quanta entries. Use “News brief” for a dispatch. Optional companion links can point to audio or related coverage. |
| CV | `assets/pdf/CV.pdf`, `_data/cv_overview.json` | Replace the PDF at its stable URL. Update the displayed revision date and the appointments, education, and honors in the HTML overview. |
| Research highlights | `_data/highlights.yml`, `assets/figures/` | Add a record with a unique ID, tab label, summary, paper link, figure, dimensions, alt text, caption, and source link. To animate a highlight, set `movie` to an MP4 path and `figure` to its poster. |
| What’s new | `_data/updates.yml` | Add a date, type, title, URL, and optional credit line. The homepage sorts entries by date. An archive item can be featured here when an announcement is appropriate. |
| Profile and funding | `_data/profile.yml`, `_pages/about.md` | Update contact information, affiliation, portrait, or award links in the data file. The opening and acknowledgment are arranged in the homepage template. |
| Navigation | `_data/navigation.yml` | Add or reorder a page title and site-relative path. The layout applies the site’s base URL. |

Page templates live in `_pages/`. The shared layout is `_layouts/plates.html`, and the shared header, footer, and research feature are in `_includes/plates/`. Page-specific styles and scripts are loaded through the `page_css` and `page_js` front matter fields. Publications and all research topics remain readable with JavaScript disabled.

## Research figures

- **Singularity formation.** Figure 1 on page 4 of Levent Alpöge and Tristan Buckmaster’s *Finite-time blow-up for the Navier–Stokes equations*. The image is the original two-panel figure, encoded losslessly as WebP. It shows the computed approximate profile at two vorticity magnitudes. [Pinned manuscript](https://github.com/tristanbuckmaster/navier-stokes/blob/b86ec358087c6d32c4bff73f4ef440f7491b426f/paper/finite-time-blow-up-navier-stokes.pdf)
- **Non-uniqueness.** One viscous animation draws the streamlines of the raw axisymmetric ring lift in a physical meridional slice. Initially the ring radii are `rₙ = R exp(nc/R)` and their core widths scale with `rₙ/R`. At physical time `t`, each radius samples the planar viscous solution at its own local age `s = R²t/r²`. The raw lift is the starting point for the paper’s curvature correction. [Construction overview, p. 6](https://hexagonmath.org/pdf/2611.00143v1#page=6) · [Ring lift, Proposition 5.1, p. 19](https://hexagonmath.org/pdf/2611.00143v1#page=19)
- **Wave turbulence.** The two Feynman trees in `assets/figures/wave-interaction-diagrams.svg` represent the cubic term in equation (3.2b) and the third-order term in Figure 1. Each vertex has the momentum rule `k = k₁ − k₂ + k₃`. Dashed branches denote conjugated factors. [Figure 1 and equation (4.2)](https://arxiv.org/pdf/1907.03667#page=12)

### Reproduce the viscous ring animation

The animation plots fixed levels of the physical stream function `r ψ(q,η,s)` in the `(r,z)` plane. The illustrative parameters are `R = 14`, `c = 6` and `ν = 1/6`. Each step toward the axis multiplies the initial ring radius by `exp(−6/14) ≈ 0.65`. The frame spans `0.235 ≤ r/R ≤ 1.26` and runs from physical time 0 to 1.25. The local planar age varies across each frame according to `s = R²t/r²`.

The generator integrates the viscous planar vorticity equation with dealiased Fourier advection and integrating-factor RK4. It interpolates the computed stream function in space and local age before applying the ring lift. Validation checks the analytic initial profile, discrete scaling, viscous energy balance, spatial and temporal refinement, and the height of the numerical cylinder.

Run with NumPy and Pillow 10.1 or newer. The macOS encoder uses AVFoundation.

```sh
python3 bin/generate-vortex-movies.py /tmp/ring-lift --validate
swiftc bin/encode-figure-frames.swift -o /tmp/encode-figure-frames
/tmp/encode-figure-frames /tmp/ring-lift/frames /tmp/viscous-ring-lift.mp4 20
```

Copy the MP4 and `/tmp/ring-lift/viscous-ring-lift-poster.webp` into `assets/figures/` to update the site. The checked-in animation plays offline.
