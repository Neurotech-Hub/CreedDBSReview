# Creed DBS architecture explorer

A static page that prices mouse DBS architecture choices in battery current and chronic lifetime.

**[Open the explorer](https://neurotech-hub.github.io/CreedDBSReview/)**

The long-form source is [`docs/architecture_review.md`](docs/architecture_review.md).

## GitHub Pages

No build step. The site is the `docs/` folder, published by
[`.github/workflows/pages.yml`](.github/workflows/pages.yml) on every push to `main`.

1. Push this repository to GitHub.
2. Open **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to **GitHub Actions**.

That is the only manual step. The workflow uploads `docs/` and deploys it, with
`docs/index.html` as the site homepage.

If you would rather not use Actions, set **Source** to **Deploy from a branch** with
**Branch** `main` and **Folder** `/docs`, and delete the workflow. `.nojekyll` is included
either way so GitHub does not run Jekyll on the folder.
