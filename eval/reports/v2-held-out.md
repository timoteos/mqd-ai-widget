# Chatbot test run 2026-11-19 00:35 UTC (v2 final: haiku-5-5, facts, keyword search, whole-site grader)

Against `lambda:medquest-kb-chat-v2`.

| Measure | Result |
|---|---|
| Passed (keyword checks) | 33 of 34 runs (97%) |
| Passed (grader, global.anthropic.claude-opus-5-5) | 91% |
| Grader averages: correct / complete / actionable (of 2), clear (of 1) | 1.88 / 1.79 / 2 / 1 |
| Questions that passed every time | 15 of 17 |
| Facts found | 97% |
| Gave the expected link | 94% |
| Self-service: gave a web address to act on | 100% |
| Told people to call when the site has the answer | 2 of 28 |
| Blocked by the guardrail | 0 |
| Median / slowest reply | 4.4s / 11.5s |

| Category | Passed | Self-service |
|---|---|---|
| Held-out | 33 of 34 | 34 of 34 |

## Failures and unneeded call referrals

### ho-going-home (Held-out) run 1

- Grader: fail, correct 0, complete 1: The answer wrongly says DHS 1167 is required for Going Home Plus (the site lists it only for long-term care applications), and it leaves out the key eligibility rules: on Medicaid, 60 or more continuous days in the facility, and nursing facility level of care.

> **Q:** My dad has been in a nursing home for months and wants to move back home. Is there a program that helps with that?
>
**Bot said:**

```
Yes. The Going Home Plus (GHP) project helps residents of hospitals, nursing facilities, and ICF/ID facilities move back into the community. It can help find housing if he doesn't have a home to return to, and arrange services such as help with cooking and bathing. Individuals from all islands are eligible. Your dad and family work with a Health Coordinator to choose a package of services and the providers they want. Services can include personal assistance, home-delivered meals, home maintenance, skilled nursing, and non-medical transportation, among others.

You can read more on the [Going Home Plus page](https://medquest.hawaii.gov/en/members-applicants/already-covered/going-home-plus) and the [GHP Eligibility Requirements](https://medquest.hawaii.gov/en/members-applicants/already-covered/going-home-plus/ghp-eligibility-requirements) page. If your dad wants to return home, he also needs to declare that intent using [Form DHS 1167, Statement of Intent to Return Home](https://medquest.hawaii.gov/api/media/file/DHS_1167_Form_Rev_12_16_Fillable.pdf).

To talk about your dad's specific situation, call the Customer Services Call Center at 1-800-316-8005 (toll-free), or 808-524-3370 on O'ahu.
```

- Told the person to call although the site answers this
- Expected: Going Home Plus helps Medicaid members who have lived in a hospital, nursing facility or ICF/ID for at least 60 days in a row move back into the community, including help finding housing and services. Open to all islands.
- Source: https://medquest.hawaii.gov/en/members-applicants/already-covered/going-home-plus

### ho-going-home (Held-out) run 2

> **Q:** My dad has been in a nursing home for months and wants to move back home. Is there a program that helps with that?
>
**Bot said:**

```
Yes. Going Home Plus (GHP) helps residents of hospitals, nursing facilities, and ICF/ID facilities move back into the community. It can help find housing if he doesn't have a home to return to, and services such as help with cooking and bathing. Individuals from all islands are eligible. You can read more on the [Going Home Plus page](https://medquest.hawaii.gov/en/members-applicants/already-covered/going-home-plus), including the [eligibility requirements](https://medquest.hawaii.gov/en/members-applicants/already-covered/going-home-plus/ghp-eligibility-requirements) and [GHP services](https://medquest.hawaii.gov/en/members-applicants/already-covered/going-home-plus/GHP-services).

If he wants to declare his intent to return home, there is also [Form DHS 1167: Statement of Intent to Return Home](https://medquest.hawaii.gov/api/media/file/DHS_1167_Form_Rev_12_16_Fillable.pdf) (fillable version), which is for people receiving long-term care services in a facility or community setting.

I don't have details on whether he specifically qualifies for GHP. For help with his case, you can call Med-QUEST Customer Service at 1-800-316-8005 (TTY 711).
```

- Told the person to call although the site answers this
- Expected: Going Home Plus helps Medicaid members who have lived in a hospital, nursing facility or ICF/ID for at least 60 days in a row move back into the community, including help finding housing and services. Open to all islands.
- Source: https://medquest.hawaii.gov/en/members-applicants/already-covered/going-home-plus

### ho-foster (Held-out) run 2

> **Q:** I aged out of foster care and I'm 22 now. Can I still get Medicaid?
>
**Bot said:**

```
You may be able to. Med-QUEST has a group for former foster care youth who are 18 through 25, and it covers people who were in foster care, kinship guardianship, or adoption assistance. At 22, you may fall in this group.

The only way to know for sure is to apply, and it's free. You can [apply online](https://medical.mybenefits.hawaii.gov) or see [all the ways to apply](https://medquest.hawaii.gov/en/members-applicants/get-started/how-to-apply). You can also ask "Do I qualify?" for a quick estimate.
```

- Missing: 26
- Expected: Yes, likely: Med-QUEST covers certain former foster care youth from 18 up to age 26. Apply to confirm.
- Source: https://medquest.hawaii.gov/en/members-applicants/get-started/programs

### ho-follow-fraud (Held-out) run 1

- Grader: fail, correct 1, complete 2: It says the hotline is for fraud 'by a QUEST Integration health plan,' but the site lists it as AlohaCare's line for reporting any suspected Medicaid fraud, waste, or abuse.

> **Q:** Which health plans can I pick from?
>
> **Q:** Which one of those has the fraud hotline 1-855-973-1852?
>
**Bot said:**

```
AlohaCare has the fraud hotline 1-855-973-1852. It is a 24/7 reporting hotline for suspected Medicaid fraud, waste, or abuse by a QUEST Integration health plan.
```

- Expected: AlohaCare's 24/7 fraud reporting hotline is 1-855-973-1852.
- Source: https://medquest.hawaii.gov/en/members-applicants/fraud-prevention

### ho-follow-fraud (Held-out) run 2

- Grader: fail, correct 1, complete 2: Right plan and number, but 'abuse by the plan' wrongly narrows the hotline to fraud by the plan itself; the site describes it as a line for reporting any suspected Medicaid fraud, waste, or abuse.

> **Q:** Which health plans can I pick from?
>
> **Q:** Which one of those has the fraud hotline 1-855-973-1852?
>
**Bot said:**

```
AlohaCare has the fraud hotline 1-855-973-1852. It's a 24/7 reporting line for suspected Medicaid fraud, waste, or abuse by the plan.
```

- Expected: AlohaCare's 24/7 fraud reporting hotline is 1-855-973-1852.
- Source: https://medquest.hawaii.gov/en/members-applicants/fraud-prevention
