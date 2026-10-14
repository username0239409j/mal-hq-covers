# mal-hq-covers

Give your MyAnimeList list high quality covers with no extensions.

MAL serves list covers as tiny ~192px thumbnails. This script reads a
list and generates `hq_example.css`: per-title overrides that swap in each cover's
full-size upload. It works for visitors too.

## Quick start

Requirements: Python 3.

    python make_hq.py --user YOUR_USERNAME

Your anime and manga lists must be Public. If they are private, save each
list page instead (right-click > View page source, save the file) and run:

    python make_hq.py --anime anime.html --manga manga.html

Either way you get an `hq_example.css` in the current folder. Re-run the python script whenever
titles are added; stale entries are harmless (rules simply stop matching).

## Host it

The file must be reachable over HTTPS **as `text/css`**. Easiest free path:

1. Fork this repo (or make your own public repo) and push your `hq_example.css`.
2. Use it through jsDelivr (correct MIME type, global CDN, free):

    https://cdn.jsdelivr.net/gh/YOURNAME/REPO@main/hq_example.css

3. After updating the file, open this once to bust the cache:

    https://purge.jsdelivr.net/gh/YOURNAME/REPO@main/hq_example.css

Alternatives that also work: Cloudflare R2, Netlify, Vercel - anything
serving static files as `text/css`.

## Apply it

Paste this as the **first line** of the MAL custom CSS box
(List Style must be Modern):

    @import url("YOUR-HOSTED-URL-GOES-HERE");

## How it works

Each rule matches one cover by its thumbnail URL fragment and paints the
large upload over it, with the original as fallback:

    .list-table .data.image:has(img[src*="/anime/6/79597."]) .link{
      background-image:url(".../79597l.jpg"), url(".../79597.jpg") !important; ...}
    .list-table .data.image:has(img[src*="/anime/6/79597."]) img{opacity:0 !important;}

Needs a browser from 2023 or newer (`:has()` support). Nothing here is
private data: titles and CDN image URLs are already public on MAL profiles.
