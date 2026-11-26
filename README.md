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
| Research highlights | `_data/highlights.yml`, `assets/figures/` | Add a record with a unique ID, tab label, summary, paper link, figure, dimensions, alt text, caption, and source link. A highlight can also have a `simulations` list. Each run has a label, viscosity and MP4 path, and the figure supplies the shared poster. List the default run first. |
| What’s new | `_data/updates.yml` | Add a date, type, title, URL, and optional credit line. The homepage sorts entries by date. An archive item can be featured here when an announcement is appropriate. |
| Profile and funding | `_data/profile.yml`, `_pages/about.md` | Update contact information, affiliation, portrait, or award links in the data file. The opening and acknowledgment are arranged in the homepage template. |
| Navigation | `_data/navigation.yml` | Add or reorder a page title and site-relative path. The layout applies the site’s base URL. |

Page templates live in `_pages/`. The shared layout is `_layouts/plates.html`, and the shared header, footer, and research feature are in `_includes/plates/`. Page-specific styles and scripts are loaded through the `page_css` and `page_js` front matter fields. Publications and all research topics remain readable with JavaScript disabled.

## Research figures

- **Singularity formation.** Figure 1 on page 4 of Levent Alpöge and Tristan Buckmaster’s *Finite-time blow-up for the Navier–Stokes equations*. The image is the original two-panel figure, encoded losslessly as WebP. It shows the computed approximate profile at two vorticity magnitudes. [Pinned manuscript](https://github.com/tristanbuckmaster/navier-stokes/blob/b86ec358087c6d32c4bff73f4ef440f7491b426f/paper/finite-time-blow-up-navier-stokes.pdf)
- **Non-uniqueness.** The two movies evolve the planar Gaussian vortex train used in §3 of the Hexagon preprint. Both start with spacing `c = 6` and the same passive tracer particles. The viscous run solves the two-dimensional Navier–Stokes vorticity equation at `ν = 1/6`. The inviscid run solves the Euler equation at `ν = 0`. They share a clock and fixed streamfunction contour levels. The non-uniqueness theorem in the paper concerns three-dimensional solutions at a single viscosity. [Planar construction, p. 8](https://hexagonmath.org/pdf/2611.00143v1#page=8)
- **Wave turbulence.** The two Feynman trees in `assets/figures/wave-interaction-diagrams.svg` represent the cubic term in equation (3.2b) and the third-order term in Figure 1. Each vertex has the momentum rule `k = k₁ − k₂ + k₃`. Dashed branches denote conjugated factors. [Figure 1 and equation (4.2)](https://arxiv.org/pdf/1907.03667#page=12)

### Reproduce the vortex simulations

The generator uses NumPy and Pillow 10.1 or newer. It evolves vorticity on a periodic box of size 6 × 30, with 64 × 320 grid points and time step 0.025. The tall transverse period approximates the paper’s infinite cylinder. The solver uses dealiased Fourier advection, integrating-factor RK4 for viscosity, and passive particles advanced with the same four velocity stages. The validation run compares both simulations against a finer mesh with half the time step and against a taller domain. It also checks the energy balance and inviscid enstrophy.

```sh
python3 bin/generate-vortex-movies.py /tmp/vortex-frames --validate
```

The output contains two frame sequences, the shared poster and a JSON validation report. Encode the frames at 20 frames per second, preserving the initial frame and the common clock through simulation time 9. On macOS the included encoder uses AVFoundation.

```sh
swiftc bin/encode-figure-frames.swift -o /tmp/encode-figure-frames
/tmp/encode-figure-frames /tmp/vortex-frames/viscous /tmp/vortex-train-evolution.mp4 20
/tmp/encode-figure-frames /tmp/vortex-frames/inviscid /tmp/vortex-train-inviscid.mp4 20
```

To update the website, copy the two MP4s and `vortex-train-poster.webp` into `assets/figures/`. The checked-in movies play without Python or Swift.
