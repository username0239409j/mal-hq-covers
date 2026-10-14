# mal-hq-covers

Give your MyAnimeList list high quality covers with no extensions for you and visitors.

MAL serves list covers as tiny ~192px thumbnails. This script reads your list
and generates `hq_example.css`: per-title overrides that swap in each cover's
full-size upload.

## Quick start

Requirements: Python 3.

    python make_hq.py --user YOUR_USERNAME

Your anime and manga lists must be Public. If they are private, save each
list page instead (right-click > View page source, save the file) and run:

    python make_hq.py --anime anime.html --manga manga.html

Either way you get an `hq_example.css` in the current folder. Re-run the
script and re-push whenever titles are added; stale entries are harmless
(rules simply stop matching).

## Host it (so visitors get it too)

The file must be reachable over HTTPS **as `text/css`**. Easiest free path
is jsDelivr on a public GitHub repo:

1. Push your `hq_example.css` to a public repo.
2. Use it through jsDelivr (correct MIME type, global CDN, free):

    https://cdn.jsdelivr.net/gh/YOURNAME/REPO@main/hq_example.css

3. Paste this as the **first line** of the MAL custom CSS box
   (List Style must be Modern):

    @\import "https://cdn.jsdelivr.net/gh/YOURNAME/REPO@main/hq_example.css";

   The backslash is intentional and required: MAL strips plain `@import`
   statements for anyone but the list owner, while browsers still parse
   `@\import` as a normal import. Without it, only you see HQ covers.
   `@import` lines must come before all other CSS, so keep this first
   (a fonts `@import` may follow it directly).

4. After updating the file, open this once to bust the CDN cache:

    https://purge.jsdelivr.net/gh/YOURNAME/REPO@main/hq_example.css

## How it works

Each rule matches one cover by its thumbnail URL fragment and paints the
large upload over it, with the original as fallback:

    .list-table .data.image:has(img[src*="/anime/6/79597."]) .link{
      background-image:url(".../79597l.jpg"), url(".../79597.jpg") !important; ...}
    .list-table .data.image:has(img[src*="/anime/6/79597."]) img{opacity:0 !important;}

Needs a browser from 2023 or newer (`:has()` support). Nothing here is
private data: titles and CDN image URLs are already public on MAL profiles.
