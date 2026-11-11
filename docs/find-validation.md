# Precovery search validation

Generated 2026-11-11T03:44:46.630Z by `worker/test/find.live.test.ts` (`.github/workflows/find-validation.yml`).

For 20 bodies JPL identified in our catalog (the ones with the most detections, from https://spherex-planet-x.bodhishanbhag.workers.dev/api/objects), the Worker's `/api/find` was run against the live JPL and IRSA services and its frames compared with the SPHEREx frames (exposure + detector) our pipeline detected each body in.

- Frames recovered: **474 of 474** (match rate 100.0%)
- Bodies with every detected frame recovered: 20 of 20
- Searches that answered: 20 of 20; median time 25.3 s

| Query | Pipeline frames | Recovered | /api/find frames | Visits | Complete | Seconds | Error |
|---|---:|---:|---:|---:|---|---:|---|
| 431 | 44 | 44 | 259 | 44 | true | 19.7 |  |
| 2399 | 38 | 38 | 408 | 71 | true | 26.3 |  |
| 4028 | 29 | 29 | 295 | 49 | true | 23.7 |  |
| 1463 | 24 | 24 | 307 | 51 | true | 27.6 |  |
| 2883 | 24 | 24 | 302 | 50 | true | 19.7 |  |
| 1669 | 23 | 23 | 319 | 62 | true | 13.5 |  |
| 902 | 22 | 22 | 314 | 60 | true | 24.3 |  |
| 4239 | 21 | 21 | 470 | 80 | true | 26.6 |  |
| 1132 | 20 | 20 | 326 | 63 | true | 33.9 |  |
| 1686 | 20 | 20 | 407 | 68 | true | 26.7 |  |
| 2116 | 20 | 20 | 302 | 54 | true | 38.4 |  |
| 2158 | 20 | 20 | 368 | 66 | true | 31.7 |  |
| 440 | 25 | 25 | 292 | 53 | true | 24.2 |  |
| 4195 | 20 | 20 | 265 | 43 | true | 16.8 |  |
| 1128 | 25 | 25 | 282 | 48 | true | 14.3 |  |
| 2400 | 19 | 19 | 441 | 77 | true | 27.9 |  |
| 3095 | 26 | 26 | 396 | 71 | true | 25.3 |  |
| 1450 | 18 | 18 | 307 | 53 | true | 32.7 |  |
| 1608 | 18 | 18 | 269 | 45 | true | 14.8 |  |
| 7043 | 18 | 18 | 327 | 55 | true | 18.3 |  |
