# Nuvio Assets — GitHub Actions Setup

Run the asset fetcher on GitHub's servers with one click. No terminal, no Python
on your machine. The workflow downloads all artwork and commits it back to the repo.

## What gets fetched (60 images total)
- 41 genre/theme images (Pexels search)
- 8 franchise fallbacks (Pexels — for franchises with no branded art)
- 11 branded franchise images (copied from rrevanth/nuvio-assets into YOUR repo)

After it runs, every image lives in your own `Sacul86/nuvio-assets` repo, so
nothing breaks if any external repo disappears.

## One-time setup

### 1. Add the two files to your repo
Put these in the repo, then commit/push (you can do this on github.com directly
via "Add file" -> "Upload files" on mobile):

- `fetch_all_assets.py`  -> repo root
- `fetch-assets.yml`     -> must go in `.github/workflows/fetch-assets.yml`
  (create the `.github/workflows/` folders; the file must be inside them)

### 2. Add your Pexels key as a secret
On github.com: your repo -> Settings -> Secrets and variables -> Actions ->
"New repository secret".
  Name:  PEXELS_API_KEY
  Value: (your key from https://www.pexels.com/api/)

Secrets are encrypted and never visible in logs.

## Running it
Repo -> Actions tab -> "Fetch Nuvio Assets" -> "Run workflow" button.
- Leave "overwrite" unticked to only fetch missing images (fast, safe).
- Tick it to re-fetch everything (e.g. if you want fresh Pexels picks).

It takes about a minute. When it finishes, the `assets/` folder is populated and
auto-committed. Check the commit appears, then import the v10 JSON in Nuvio.

## Import in Nuvio
nuvioapp.space -> right profile -> Collections -> Import JSON ->
`carl-nuvio-themed-collections-v10.json` -> Replace profile collections.

## Notes
- The workflow needs no personal access token — it uses the built-in
  GITHUB_TOKEN with `contents: write` permission (already set in the yml).
- `[skip ci]` is in the commit message so the commit doesn't re-trigger anything.
- To re-tune an image: edit the search query in `fetch_all_assets.py`, commit,
  then run the workflow with overwrite ticked (or delete that one file first and
  run without overwrite).
- Branch note: your repo's default branch is `master`, and the v10 JSON points at
  `/master/`. If you ever rename it to `main`, update the URLs in the JSON too.
