# Sample runs

Every quiz file here was produced by `scripts/make_sample.py` with a real model call, not hand written. The source texts are stored verbatim in `sumber/` so each evidence quote can be checked against the original.

| Quiz | Source file | Source | Retrieved | Items |
|---|---|---|---|---|
| `jakarta-harga-properti.json` | `sumber/bi-shpr-2026-q3.txt` | Bank Indonesia, Survei Harga Properti Residensial triwulan III 2026, siaran pers 6 November 2026 | 6 November 2026 | 4 |
| `kpr-flpp.json` | `sumber/pkp-flpp-btn-2026-11-02.txt` | Kementerian Perumahan dan Kawasan Permukiman, 2 November 2026 | 6 November 2026 | 5 |

Sources:

- https://www.bi.go.id/id/publikasi/ruang-media/news-release/Pages/sp_2824426.aspx
- https://pkp.go.id/berita/detail/menteri-pkp-minta-btn-percepat-penyaluran-kur-perumahan-dan-kpr-flpp-untuk-mbr

To check that every quote is real, compare `evidence_quote` in each JSON file with the text in `sumber/`. The test suite does the same check in `tests/test_evidence.py` with a scripted provider.

No internal 99 Group document is used here. Both sources are public government releases.
