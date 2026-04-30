# Book Author URL Spot-Check Guide

Generated: March 20, 2026

Use this document to spot-check authors who already have URLs, and manually update the ones still missing.

## Summary

| Status | Count |
|--------|-------|
| Has URL (auto-populated from article data) | 47 |
| Missing URL (needs manual update) | 68 |
| Not found in database | 5 |
| **Total unique book authors** | **120** |

## How to Update an Author

```bash
export API_URL="https://mcpress-chatbot-staging.up.railway.app"

# Update a single author's site_url
curl -X PATCH "$API_URL/api/authors/AUTHOR_ID" \
  -H "Content-Type: application/json" \
  -d '{"site_url": "https://the-url-here"}'
```

---

## Section 1: Authors WITH URLs (Spot-Check These)

These were auto-populated from the article Excel backfill. Verify the URLs look correct.

| ID | Author | site_url | Docs |
|----|--------|----------|------|
| 8396 | Anant Jhingran | https://www.mcpressonline.com/archive/authors/author/131082 | 2 |
| 8375 | Ashok K. Iyengar | https://www.mcpressonline.com/archive/authors/author/131082 | 2 |
| 7767 | Bob Cozzi | https://www.mcpressonline.com/archive/authors/author/66018 | 2 |
| 8392 | Bryan Meyers | https://www.mcpressonline.com/archive/authors/author/12239 | 3 |
| 7755 | Chris Peters | https://www.mcpressonline.com/archive/authors/author/65845 | 49 |
| 8382 | Colette Burrus | https://www.mcpressonline.com/archive/authors/author/12528 | 4 |
| 8454 | Colleen Garton | https://www.mcpressonline.com/archive/authors/author/75754 | 21 |
| 8412 | Cristian Molaro | https://www.mcpressonline.com/archive/authors/author/128187 | 3 |
| 8351 | David Shirey | https://www.mcpressonline.com/archive/authors/author/129607 | 148 |
| 12485 | Don Denoncourt | https://www.mcpressonline.com/archive/authors/author/65529 | 65 |
| 8545 | Don Yantzi | https://www.mcpressonline.com/archive/authors/author/68898 | 3 |
| 7758 | George Farr | https://www.mcpressonline.com/archive/authors/author/65888 | 2 |
| 8488 | Graham Williamson | https://www.mcpressonline.com/archive/authors/author/135214 | 13 |
| 8500 | Jack Beach | https://www.mcpressonline.com/archive/authors/author/131172 | 2 |
| 8538 | Jeff Olen | https://www.mcpressonline.com/archive/authors/author/65907 | 32 |
| 7736 | Jim Buck | https://www.mcpressonline.com/archive/authors/author/8807 | 41 |
| 8450 | Jim Martin | https://www.mcpressonline.com/archive/authors/author/35201 | 37 |
| 7774 | Joe Pluta | https://www.mcpressonline.com/archive/authors/author/1269 | 365 |
| 8389 | Joel Klebanoff | https://www.mcpressonline.com/archive/authors/author/20724 | 13 |
| 8352 | John Boyer | https://www.mcpressonline.com/archive/authors/author/131246 | 2 |
| 7742 | John Campbell | https://www.mcpressonline.com/archive/authors/author/131337 | 5 |
| 39999 | Kameron Cole | https://www.mcpressonline.com/archive/authors/author/65940 | 1 |
| 8443 | Ken Milberg | https://www.mcpressonline.com/archive/authors/author/128759 | 1 |
| 8359 | Kevin Schroeder | https://www.mcpressonline.com/archive/authors/author/127699 | 7 |
| 8529 | Kevin Vandever | https://www.mcpressonline.com/archive/authors/author/69165 | 3 |
| 8436 | Laura Ubelhor | https://www.mcpressonline.com/archive/authors/author/46165 | 9 |
| 7738 | Mark Simmonds | https://www.mcpressonline.com/archive/authors/author/136426 | 16 |
| 8493 | Mickey Iqbal | https://www.mcpressonline.com/archive/authors/author/130999 | 2 |
| 7726 | Mike Faust | https://www.mcpressonline.com/archive/authors/author/24916 | 67 |
| 8400 | Mohankumar Saraswatipura | https://www.mcpressonline.com/archive/authors/author/134122 | 9 |
| 8546 | Nazmin Haji | https://www.mcpressonline.com/archive/authors/author/68898 | 3 |
| 7772 | Paul Tuohy | https://www.mcpressonline.com/archive/authors/author/65987 | 10 |
| 8446 | Rafael Victoria-Pereira | https://www.mcpressonline.com/archive/authors/author/51507 | 206 |
| 8530 | Richard Dolewski | https://www.mcpressonline.com/archive/authors/author/133532 | 3 |
| 7747 | Roger E. Sanders | https://www.mcpressonline.com/archive/authors/author/68874 | 8 |
| 8379 | Roger Sanders | https://www.mcpressonline.com/archive/authors/author/68874 | 30 |
| 7770 | Ruiping Li | https://www.mcpressonline.com/archive/authors/author/132509 | 2 |
| 15428 | Shannon O'Donnell | https://www.mcpressonline.com/archive/authors/author/66028 | 71 |
| 7739 | Sunil Soares | https://www.mcpressonline.com/archive/authors/author/131010 | 16 |
| 7746 | Susan Lawson | https://www.mcpressonline.com/archive/authors/author/131223 | 5 |
| 8390 | Ted Holt | https://www.mcpressonline.com/archive/authors/author/1818 | 105 |
| 8464 | Thanh Pham | https://www.mcpressonline.com/archive/authors/author/117558 | 1 |
| 7730 | Thomas Snyder | https://www.mcpressonline.com/archive/authors/author/68692 | 64 |
| 8355 | Tracy Harris | https://www.mcpressonline.com/archive/authors/author/131577 | 3 |

---

## Section 2: Authors MISSING URLs (Update These)

These book authors have no `site_url` in the database. Find their MC Press author page and update using the curl command above.

| ID | Author | Docs | Update Command |
|----|--------|------|----------------|
| 8461 | Anant Jhingran | 1 | `curl -X PATCH "$API_URL/api/authors/8461" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8466 | Ashok K. Iyengar | 2 | `curl -X PATCH "$API_URL/api/authors/8466" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8445 | Ben Margolis | 3 | `curl -X PATCH "$API_URL/api/authors/8445" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 7735 | Bill Frank | 2 | `curl -X PATCH "$API_URL/api/authors/7735" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8354 | Brian Green | 2 | `curl -X PATCH "$API_URL/api/authors/8354" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8358 | Carlton Doe | 1 | `curl -X PATCH "$API_URL/api/authors/8358" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8516 | Cayce Marston | 1 | `curl -X PATCH "$API_URL/api/authors/8516" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8442 | Cheranellore Vasudevan | 1 | `curl -X PATCH "$API_URL/api/authors/8442" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8421 | Chris Crone | 1 | `curl -X PATCH "$API_URL/api/authors/8421" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8495 | Chris Molloy | 1 | `curl -X PATCH "$API_URL/api/authors/8495" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8437 | Christian Hur | 1 | `curl -X PATCH "$API_URL/api/authors/8437" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8366 | Christian Lau | 1 | `curl -X PATCH "$API_URL/api/authors/8366" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8365 | Colin Yu | 1 | `curl -X PATCH "$API_URL/api/authors/8365" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8410 | Daniel Luksetich | 2 | `curl -X PATCH "$API_URL/api/authors/8410" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 7741 | Dave Beulke | 1 | `curl -X PATCH "$API_URL/api/authors/7741" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8489 | David Yip | 1 | `curl -X PATCH "$API_URL/api/authors/8489" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8480 | Dinesh D. Dattani | 1 | `curl -X PATCH "$API_URL/api/authors/8480" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 7766 | Doug Pence | 3 | `curl -X PATCH "$API_URL/api/authors/7766" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8380 | Dr. Arvind Sathi | 2 | `curl -X PATCH "$API_URL/api/authors/8380" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8378 | Dr. Jean-Francois Puget | 1 | `curl -X PATCH "$API_URL/api/authors/8378" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8494 | Dr. Mithkal Smadi | 1 | `curl -X PATCH "$API_URL/api/authors/8494" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8429 | Dwaine R. Snow | 1 | `curl -X PATCH "$API_URL/api/authors/8429" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8367 | Ellen McKay | 1 | `curl -X PATCH "$API_URL/api/authors/8367" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8455 | Erika McCulloch | 1 | `curl -X PATCH "$API_URL/api/authors/8455" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8521 | Fred A. Kulack | 1 | `curl -X PATCH "$API_URL/api/authors/8521" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8422 | Gareth Jones | 1 | `curl -X PATCH "$API_URL/api/authors/8422" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8368 | Gary Flood | 1 | `curl -X PATCH "$API_URL/api/authors/8368" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8490 | Ilan Sharoni | 1 | `curl -X PATCH "$API_URL/api/authors/8490" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8395 | James Cooper | 1 | `curl -X PATCH "$API_URL/api/authors/8395" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8369 | James Hunter | 1 | `curl -X PATCH "$API_URL/api/authors/8369" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8364 | Jane Fung | 1 | `curl -X PATCH "$API_URL/api/authors/8364" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8468 | Jane Man | 1 | `curl -X PATCH "$API_URL/api/authors/8468" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 7760 | Jerry Fottral | 2 | `curl -X PATCH "$API_URL/api/authors/7760" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8374 | Joe Winchester | 1 | `curl -X PATCH "$API_URL/api/authors/8374" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8513 | Joey Bernal | 1 | `curl -X PATCH "$API_URL/api/authors/8513" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8415 | Judy H. Nall | 2 | `curl -X PATCH "$API_URL/api/authors/8415" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8506 | Kelvin K. A. Looi | 1 | `curl -X PATCH "$API_URL/api/authors/8506" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8457 | Kevin Forsythe | 3 | `curl -X PATCH "$API_URL/api/authors/8457" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8502 | Kevin Wegryn | 1 | `curl -X PATCH "$API_URL/api/authors/8502" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8532 | Namik Hrle | 1 | `curl -X PATCH "$API_URL/api/authors/8532" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 7775 | Owen Cline | 1 | `curl -X PATCH "$API_URL/api/authors/7775" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8470 | Pallavi Priyadarshini | 1 | `curl -X PATCH "$API_URL/api/authors/8470" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8456 | Paul H. Harkins | 1 | `curl -X PATCH "$API_URL/api/authors/8456" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8514 | Peter Blinstrubas | 1 | `curl -X PATCH "$API_URL/api/authors/8514" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8373 | Peter Walker | 1 | `curl -X PATCH "$API_URL/api/authors/8373" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8497 | Phil Coulthard | 1 | `curl -X PATCH "$API_URL/api/authors/8497" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 7745 | Philip K. Gunning | 1 | `curl -X PATCH "$API_URL/api/authors/7745" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8548 | Rama Turaga | 1 | `curl -X PATCH "$API_URL/api/authors/8548" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 7749 | Ranjan Sinha | 1 | `curl -X PATCH "$API_URL/api/authors/7749" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8401 | Robert (Kent) Collins | 1 | `curl -X PATCH "$API_URL/api/authors/8401" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8362 | Robert McChesney | 1 | `curl -X PATCH "$API_URL/api/authors/8362" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8406 | Roger Miller | 1 | `curl -X PATCH "$API_URL/api/authors/8406" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8512 | Ron Lynn | 1 | `curl -X PATCH "$API_URL/api/authors/8512" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8467 | Shantan Kethireddy | 1 | `curl -X PATCH "$API_URL/api/authors/8467" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8462 | Stephan Jou | 1 | `curl -X PATCH "$API_URL/api/authors/8462" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8383 | Stephanie Parkin | 2 | `curl -X PATCH "$API_URL/api/authors/8383" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8376 | Steven Astorino | 3 | `curl -X PATCH "$API_URL/api/authors/8376" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8407 | Surekha Parekh | 7 | `curl -X PATCH "$API_URL/api/authors/8407" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8418 | Terry Purcell | 2 | `curl -X PATCH "$API_URL/api/authors/8418" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8517 | Tim Hanis | 1 | `curl -X PATCH "$API_URL/api/authors/8517" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8370 | Tim deBoer | 1 | `curl -X PATCH "$API_URL/api/authors/8370" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8515 | Usman Memon | 1 | `curl -X PATCH "$API_URL/api/authors/8515" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8371 | Valentina Birsan | 1 | `curl -X PATCH "$API_URL/api/authors/8371" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8518 | Varadarajan (Varad) Ramamoorthy | 1 | `curl -X PATCH "$API_URL/api/authors/8518" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8448 | Vedish Shah | 1 | `curl -X PATCH "$API_URL/api/authors/8448" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8486 | Venkata Gadepalli | 1 | `curl -X PATCH "$API_URL/api/authors/8486" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8463 | William Lee | 1 | `curl -X PATCH "$API_URL/api/authors/8463" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |
| 8372 | Yen Lu | 1 | `curl -X PATCH "$API_URL/api/authors/8372" -H "Content-Type: application/json" -d '{"site_url": "URL_HERE"}'` |

---

## Section 3: Authors NOT Found in Database

These names appear in the book Excel but weren't found in the authors table. They may have been parsed differently or not imported.

| Author Name | Notes |
|-------------|-------|
| Chuck Stupca | Not in DB — may need manual creation |
| Gary Craig | Not in DB — may need manual creation |
| MC Press Bookstore | Not a real author — likely a placeholder |
| Pete Helgren | Not in DB — may need manual creation |
| Peter Jakab | Not in DB — may need manual creation |

---

## Quick Verification Commands

```bash
export API_URL="https://mcpress-chatbot-staging.up.railway.app"

# Check a specific author's current status
curl -s "$API_URL/api/authors/search?q=Jim+Buck" | python3 -m json.tool

# Verify an author after updating
curl -s "$API_URL/api/authors/7736" | python3 -m json.tool

# List all documents by an author
curl -s "$API_URL/api/authors/7736/documents" | python3 -m json.tool
```
