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
| Research highlights | `_data/highlights.yml`, `assets/figures/` | Add or edit a record with a unique ID, tab label, summary, paper link, and figure. Include the image dimensions, alt text, caption, and source link. The order in the file sets the order of the tabs. |
| What’s new | `_data/updates.yml` | Add a date, type, title, URL, and optional credit line. The homepage sorts entries by date. An archive item can be featured here when an announcement is appropriate. |
| Profile and funding | `_data/profile.yml`, `_pages/about.md` | Update contact information, affiliation, portrait, or award links in the data file. The opening and acknowledgment are arranged in the homepage template. |
| Navigation | `_data/navigation.yml` | Add or reorder a page title and site-relative path. The layout applies the site’s base URL. |

Page templates live in `_pages/`. The shared layout is `_layouts/plates.html`, and the shared header, footer, and research feature are in `_includes/plates/`. Page-specific styles and scripts are loaded through the `page_css` and `page_js` front matter fields. Publications and all research topics remain readable with JavaScript disabled.

## Research figures

- **Singularity formation.** Figure 1 on page 4 of Levent Alpöge and Tristan Buckmaster’s *Finite-time blow-up for the Navier–Stokes equations*. The image is the original two-panel figure, encoded losslessly as WebP. It shows the computed approximate profile at two vorticity magnitudes. [Pinned manuscript](https://github.com/tristanbuckmaster/navier-stokes/blob/b86ec358087c6d32c4bff73f4ef440f7491b426f/paper/finite-time-blow-up-navier-stokes.pdf)
- **Non-uniqueness.** Original vector rendering of the initial periodic Gaussian stream function in §3, page 8, of Tristan Buckmaster, Matei P. Coiculescu, and Chen Li’s *Non-Uniqueness of Leray–Hopf Solutions to the Unforced Three-Dimensional Navier–Stokes Equations*. The illustrative spacing is c = 6. Regenerate the SVG with `python3 bin/draw_vortex_train.py`. [Hexagon preprint](https://hexagonmath.org/2611.00143v1) · [Formula on page 8](https://hexagonmath.org/pdf/2611.00143v1#page=8)
- **Wave turbulence.** An illustrative Fourier lattice shows the resonant quartet (1,0), (3,1), (2,3), (0,2). The two pairs of opposite vertices have equal sums of wave vectors and equal sums of squared lengths. [Related paper](https://doi.org/10.1007/s00222-021-01039-z)
