# Payment Provider Decision Record — P4-7

**Date:** 2026-06-13  
**Status:** DECIDED — Razorpay for India-first, Stripe as future international path  
**Owner:** Nishant  

---

## Context

Swaya.me needs a payment provider to power self-serve plan upgrades (P4-3).
The platform serves Indian educational institutions primarily; global expansion is on the 2027 roadmap.
The existing tier system (FREE / BASIC / PRO / ENTERPRISE) is enforced via `TierService` + Redis;
JWT tier-stale bug was fixed post-2026-06-01 so tier changes propagate without re-login.

---

## Options evaluated

| Factor | Razorpay | Stripe |
|---|---|---|
| **Indian audience** | Native INR, UPI, NetBanking, EMI, wallets | INR supported but checkout UX is foreign |
| **Global audience** | Limited outside India/SE Asia | Industry standard worldwide |
| **MDR / fees** | 2% flat (no monthly fee on basic) | 2.9% + ₹25 per transaction |
| **Subscription API** | Razorpay Subscriptions — plans + webhooks | Stripe Billing — battle-tested |
| **Webhook reliability** | Good; retries for 24 h | Excellent; retry with exponential backoff |
| **Integration surface** | `razorpay` Python SDK + JS checkout modal | `stripe` Python SDK + Stripe.js |
| **PCI scope** | Tokenized; no card data touches server | Same |
| **Setup complexity** | KYC in 1–2 days, sandbox instant | KYC in 1–2 days, sandbox instant |
| **Trial/coupon support** | Yes (add-on feature) | Yes (built-in) |
| **Team familiarity** | Low | Low (equal) |

---

## Decision

**Use Razorpay** for the P4-3 self-serve flow.

Rationale:
1. >90% of current tenants are Indian institutions — native UPI/NetBanking is essential for conversion.
2. Lower effective fee for the INR price points we'll set (BASIC ₹999/mo, PRO ₹2999/mo).
3. Razorpay Subscriptions handles recurring billing, prorations, and webhooks adequately.
4. Stripe can be layered in later for international tenants behind a `currency` switch — the TierService abstraction makes this feasible without a rewrite.

**Architecture:** `backend/features/billing/` — thin service wrapping Razorpay Subscriptions API,
webhook endpoint at `/api/v1/billing/webhook` (HMAC-verified), tier change propagated via
`TierService.set_tier(tenant_id, tier, valid_until)` which writes Redis and invalidates JWT cache.

**Secret storage:** `RAZORPAY_KEY_ID` + `RAZORPAY_KEY_SECRET` in `.env` / OCI Vault.

---

## What P4-3 needs to implement

1. `POST /billing/create-subscription` — creates Razorpay subscription, returns checkout session ID
2. `POST /billing/webhook` — HMAC verify → update tier in TierService
3. `GET /billing/portal` — returns Razorpay dashboard link for self-service cancellation
4. Frontend: Plans page "Upgrade" button → Razorpay checkout modal → success redirect
5. Email confirmation on tier change (reuse existing email infrastructure)

---

## Not in scope for P4-3

- Prorated mid-cycle upgrades (use period end)
- Team/seat-based billing (P4-5 milestone)
- International currencies (Stripe layer, post-2026)
- Invoice PDF generation (Razorpay auto-generates)
