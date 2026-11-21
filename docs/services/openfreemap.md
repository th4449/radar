# OpenFreeMap map tiles

- Used by: the public site's maps, `web/src/components/AlertMap.tsx`
- Service: https://openfreemap.org/
- Terms: https://openfreemap.org/tos/, last updated October 14, 2026
- Checked: November 20, 2026
- Result: **allowed.** Not a record source. A visitor's browser loads map tiles from it.

## What was verified

- **Free, with no key.** The start page says the public instance has no limit on map views or requests, no registration and no API key.
- **Commercial and public use is allowed.** The page answers the question with one word: yes.
- **Attribution is required.** With MapLibre it is added to the map automatically. The site also names OpenFreeMap and OpenStreetMap on the methodology page.
- **What the terms bar.** Illegal use, disrupting the service, and collecting data from it in automated ways. The site does none of these. It draws a map in a visitor's browser.
- **No promise of service.** The terms say the service is provided as it is and may be discontinued at any time without notice.
- The map data is OpenStreetMap's, under its own license.

## What the site does

- Loads the style `https://tiles.openfreemap.org/styles/positron` in MapLibre GL JS 6.19.0.
- Loads the map library only on a page that has a located alert to show.
- Shows every alert in a list under the map. If the map fails, the page says so and loses nothing.

## What this means for a visitor

A visitor's browser asks OpenFreeMap's servers for tiles, so those servers see the visitor's address. The terms say OpenFreeMap may serve content through Cloudflare. The radar sends them nothing else.

## What was not verified

- OpenFreeMap's privacy page. It was not read.
- How the service behaves under load, or how often it is down.
- A run of the map from a hosted copy of the site. It was seen on a developer's machine only.

## If it goes away

The map is one component. Another MapLibre style address replaces it. OpenFreeMap also publishes its tiles for self-hosting.
