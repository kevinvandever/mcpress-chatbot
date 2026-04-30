# Freemium Usage Gate — Current State & Options

## Current Implementation (Deployed to Staging)

**Approach:** Anonymous fingerprint-based tracking

- Visitors can use the chatbot immediately with no login required
- A browser fingerprint (stored in localStorage) tracks usage per browser
- After N free questions (configurable via `ANON_QUESTION_LIMIT` env var), a paywall overlay appears prompting login/subscription
- Backend tracks usage in a `usage_tracking` table keyed by anonymous ID
- Frontend shows a "remaining questions" banner as the user approaches the limit

**Known Weakness:** The fingerprint is per-browser, not per-person. Users can reset their free questions by:
- Switching to a different browser
- Using incognito/private mode
- Clearing localStorage

**Env Vars:**
- `ANON_QUESTION_LIMIT` — number of free questions (default: 3)

---

## Options Under Consideration

### Option A: Keep Current (Anonymous Fingerprint)

| Pros | Cons |
|------|------|
| Zero friction — anyone can try instantly | Trivially bypassed across browsers |
| Good for SEO/discovery traffic | No email capture for marketing |
| Simplest implementation (already done) | Can't identify or follow up with users |

**Best for:** Maximizing top-of-funnel engagement, low-commitment product demos.

### Option B: Registration Required Before Any Questions

| Pros | Cons |
|------|------|
| Accurate per-user tracking (one account per email) | Higher friction — some visitors will bounce |
| Captures email for marketing/follow-up | Requires email verification to prevent throwaway signups |
| Much harder to game | More implementation work (registration flow changes) |
| Establishes a real user relationship | |

**Best for:** Lead generation, accurate usage analytics, tighter gate control.

### Option C: Hybrid — 1 Free Anonymous Question, Then Registration Wall

| Pros | Cons |
|------|------|
| Instant value demonstration (user sees it works) | Still 1 free question per browser (minor leakage) |
| Registration feels justified after seeing quality | Slightly more complex UX flow |
| Captures email after proving value | |
| Common SaaS pattern (ChatGPT, etc.) | |

**Best for:** Balancing discovery with lead capture. Recommended approach for IBM i professional audience who are actively seeking technical answers and accustomed to signing up for tools.

---

## Recommendation

Option C (hybrid) is likely the sweet spot. IBM i professionals aren't casual browsers — they're looking for specific technical help. One free answer hooks them, and registration to continue is a reasonable ask. This gives you reliable tracking, email capture, and minimal leakage while still letting the product sell itself.

---

*Decision pending — discussing with business partner. Will update this doc with chosen direction.*
