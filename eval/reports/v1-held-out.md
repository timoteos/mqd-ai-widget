# Chatbot test run 2026-11-19 00:39 UTC (v1 live: haiku-4-5, old knowledge bases)

Against `v1 API Gateway (address in .env)`.

| Measure | Result |
|---|---|
| Passed (keyword checks) | 20 of 34 runs (59%) |
| Passed (grader, global.anthropic.claude-opus-5-5) | 32% |
| Grader averages: correct / complete / actionable (of 2), clear (of 1) | 1.62 / 0.85 / 1.47 / 0.88 |
| Questions that passed every time | 4 of 17 |
| Facts found | 62% |
| Gave the expected link | 6% |
| Self-service: gave a web address to act on | 6% |
| Told people to call when the site has the answer | 25 of 28 |
| Blocked by the guardrail | 0 |
| Median / slowest reply | 2.7s / 6.1s |

| Category | Passed | Self-service |
|---|---|---|
| Held-out | 20 of 34 | 2 of 34 |

## Failures and unneeded call referrals

### ho-fraud (Held-out) run 1

- Grader: fail, correct 1, complete 1: The site sends all suspected recipient fraud to the BESSD Investigations Office (808-587-8444), not the call center as the answer says for 'other eligibility concerns'; it also omits the health plan fraud hotlines.

> **Q:** How do I report someone who is getting Medicaid but shouldn't be?
>
**Bot said:**

```
If you suspect someone is improperly using Medicaid:

**For Medicaid fraud or misuse of a Medicaid card:**
Call the **Medicaid Fraud Line at (808) 587-8444**

This includes if someone is selling, changing, or letting someone else use their Medicaid card.

**For other concerns about someone's eligibility:**
Call **Med-QUEST at 1-800-316-8005**
```

- Told the person to call although the site answers this
- Expected: Call the Investigations Office of the Benefits, Employment & Support Services Division at (808) 587-8444. Each health plan also has a fraud hotline.
- Source: https://medquest.hawaii.gov/en/members-applicants/fraud-prevention

### ho-ombudsman (Held-out) run 1

- Grader: fail, correct 2, complete 0: Leaves out the Medicaid Ombudsman (1-888-488-7988), the main help for unresolved health plan complaints, and pads the answer with discrimination-complaint details the person didn't ask about.

> **Q:** My health plan keeps ignoring my complaint. Who else can help me?
>
**Bot said:**

```
Here are your options:

**File a formal grievance or appeal with your health plan:**
Your health plan has a member grievance and appeal process. Contact your health plan using the number on the back of your membership card.

**Contact Med-QUEST directly:**
Call Med-QUEST at **1-800-316-8005** (or 524-3370 on Oahu). TTY/TDD: 711.

**File a discrimination complaint** (if your issue involves discrimination):
- **Hawaii Department of Human Services:**
  - Phone: (808) 586-4955 or 711
  - Mail: Box 339, Honolulu, Hawaii 96809-0339
  - Email: [email protected]
  - Online forms available at http://humanservices.hawaii.gov (Civil Rights Corner)

- **U.S. Department of Health and Human Services, Office for Civil Rights:**
  - Phone: 1-800-368-1019 or 800-537-7697 (TDD)
  - Mail: 200 Independence Avenue, SW, Room 509F, Washington, D.C. 20201
  - Online portal: https://ocrportal.hhs.gov/ocr/portal/lobby.jsf

**You can also switch health plans** if you've been with your current plan for at least 12 months.
```

- Missing: ombudsman; 488-7988
- Told the person to call although the site answers this
- Expected: The Hawaii Medicaid Ombudsman helps members with problems with their QUEST Integration health plan, including grievances and appeals: toll-free 1-888-488-7988, O'ahu (808) 746-3324, TTY 711.
- Source: https://medquest.hawaii.gov/en/resources/medicaid-ombudsman

### ho-ombudsman (Held-out) run 2

- Grader: fail, correct 1, complete 1: It leaves out the Medicaid Ombudsman (1-888-488-7988), the main resource for health plan complaints, adds an unsupported claim that the call center escalates complaints, and pads the answer with a garbled discrimination-complaint section.

> **Q:** My health plan keeps ignoring my complaint. Who else can help me?
>
**Bot said:**

```
If your health plan isn't responding to your complaint, here are your options:

**File a Formal Grievance or Appeal**
Contact your health plan directly using the number on the back of your membership card. Your health plan is required to have a member grievance and appeal process.

**Contact Med-QUEST**
Call Med-QUEST at **1-800-316-8005** (or 524-3370 on Oahu). They can help escalate your complaint.

**File a Discrimination Complaint (if applicable)**
If you believe you've been treated unfairly based on race, color, national origin, sex, age, or disability, you can file a discrimination complaint with:

- **Hawaii Department of Human Services**
  - Phone: (808) 586-4955 or 711 for relay
  - Mail: Box 339, Honolulu, Hawaii 96809-0339
  - Email: [email protected]
  - Online forms: http://humanservices.hawaii.gov (Civil Rights Corner)

- **U.S. Department of Health and Human Services, Office for Civil Rights**
  - Phone: 1-800-368-1019 (or 800-537-7697 TDD)
  - Mail: 200 Independence Avenue, SW, Room 509F, HHH Building, Washington, D.C. 20201
  - Online: https://ocrportal.hhs.gov/ocr/portal/lobby.jsf
```

- Missing: ombudsman; 488-7988
- Told the person to call although the site answers this
- Expected: The Hawaii Medicaid Ombudsman helps members with problems with their QUEST Integration health plan, including grievances and appeals: toll-free 1-888-488-7988, O'ahu (808) 746-3324, TTY 711.
- Source: https://medquest.hawaii.gov/en/resources/medicaid-ombudsman

### ho-going-home (Held-out) run 1

- Grader: fail, correct 1, complete 1: Invents a 'coordinating with financial institutions' service, sends the person to KOLEA, which is for applying for Medicaid, and omits the Going Home Plus page, eligibility rules (Medicaid, 60+ continuous days in a facility, nursing facility level of care) and health plan GHP contacts.

> **Q:** My dad has been in a nursing home for months and wants to move back home. Is there a program that helps with that?
>
**Bot said:**

```
Yes. Med-QUEST has the **Going Home Plus (GHP) Project**, which assists people who want to return home from nursing facilities or medical institutions.

Going Home Plus can help with:
- Housing applications and support
- Coordinating with financial institutions and housing agencies
- Planning the transition back home

**Next steps:**

Contact Med-QUEST to learn more about this program and your dad's eligibility:
- **Phone:** 1-800-316-8005
- **Online:** Apply or get more information through KOLEA

They can discuss your dad's specific situation and what support is available.
```

- Told the person to call although the site answers this
- Expected: Going Home Plus helps Medicaid members who have lived in a hospital, nursing facility or ICF/ID for at least 60 days in a row move back into the community, including help finding housing and services. Open to all islands.
- Source: https://medquest.hawaii.gov/en/members-applicants/already-covered/going-home-plus

### ho-going-home (Held-out) run 2

- Grader: fail, correct 1, complete 1: It invents 'coordinating with financial institutions,' misses the eligibility rules (Medicaid plus 60 continuous days in a facility) and the main services, and gives no link to the Going Home Plus page.

> **Q:** My dad has been in a nursing home for months and wants to move back home. Is there a program that helps with that?
>
**Bot said:**

```
Yes. Med-QUEST has the **Going Home Plus (GHP) Project**, which helps people transition from nursing facilities back to their homes.

Going Home Plus can assist with:
- Housing applications and support
- Coordinating with financial institutions and housing agencies
- Planning the move home

**Next steps:**
Contact Med-QUEST at **1-800-316-8005** to learn more about Going Home Plus and whether your dad qualifies. You can also ask about the **DHS 1167 form** ("Statement of Intent to Return Home"), which documents his plan to return home.
```

- Told the person to call although the site answers this
- Expected: Going Home Plus helps Medicaid members who have lived in a hospital, nursing facility or ICF/ID for at least 60 days in a row move back into the community, including help finding housing and services. Open to all islands.
- Source: https://medquest.hawaii.gov/en/members-applicants/already-covered/going-home-plus

### ho-sms-stop (Held-out) run 1

- Grader: fail, correct 2, complete 0: Says it doesn't know and sends the person to call, when the site says to text STOP to 45421 to unsubscribe.

> **Q:** How do I stop getting text messages from Med-QUEST?
>
**Bot said:**

```
I don't have that information. Please call Med-QUEST Customer Service at 1-800-316-8005 (TTY/TDD 711). They can help you manage your communication preferences.
```

- Missing: STOP; 45421
- Told the person to call although the site answers this
- Expected: Text STOP to 45421; you'll get a confirmation and no more messages. Text HELP to 45421 for help.
- Source: https://medquest.hawaii.gov/en/sms

### ho-sms-stop (Held-out) run 2

- Grader: fail, correct 2, complete 0: The bot said it lacked the answer instead of telling the person to text STOP to 45421, which is on the site, and sent them to call.

> **Q:** How do I stop getting text messages from Med-QUEST?
>
**Bot said:**

```
I don't have that information. Please call Med-QUEST Customer Service at 1-800-316-8005 (TTY/TDD 711). They can help you manage your communication preferences.
```

- Missing: STOP; 45421
- Told the person to call although the site answers this
- Expected: Text STOP to 45421; you'll get a confirmation and no more messages. Text HELP to 45421 for help.
- Source: https://medquest.hawaii.gov/en/sms

### ho-epsdt (Held-out) run 1

> **Q:** What is EPSDT?
>
**Bot said:**

```
EPSDT stands for **Early and Periodic Screening, Diagnosis and Treatment**.

It is the Medicaid program for children and young adults **under age 21**.

**EPSDT covers:**
- Complete medical, mental and behavioral health, and dental care
- Developmental, autism, and lead screening
- Intensive behavioral therapies such as applied behavioral analysis (ABA) services for members with autism spectrum disorder (ASD)
- Hearing, vision, and laboratory tests
- Immunizations and tuberculosis and skin tests
- Help setting up appointments

For more information, call your health plan or Med-QUEST at 1-800-316-8005.
```

- Told the person to call although the site answers this
- Expected: Early and Periodic Screening, Diagnostic and Treatment: preventive and comprehensive care (medical, mental and behavioral health, dental, treatment) for Medicaid members from birth up to age 21.
- Source: https://medquest.hawaii.gov/en/members-applicants/quest-integration-coverage/epsdt

### ho-ride-notice (Held-out) run 1

- Grader: fail, correct 2, complete 0: The bot claims not to have information that is on the NEMT page: book at least 48 hours ahead through your health plan, with less notice allowed for urgent visits, and it points to the Med-QUEST call center instead of the health plan.

> **Q:** How far ahead do I have to schedule a ride to my doctor?
>
**Bot said:**

```
I don't have that information. Please call Med-QUEST at 1-800-316-8005.

They can tell you the scheduling requirements for transportation to your medical appointments.
```

- Missing: 48
- Told the person to call although the site answers this
- Expected: At least 48 hours before the appointment, through your health plan; urgent visits within 24 hours can be booked with less notice.
- Source: https://medquest.hawaii.gov/en/members-applicants/quest-integration-coverage/nemt

### ho-ride-notice (Held-out) run 2

- Grader: fail, correct 2, complete 0: Claims not to have the answer, though the site says to book rides through your health plan at least 48 hours ahead (less notice for urgent visits), and sends the person to Med-QUEST instead of their plan.

> **Q:** How far ahead do I have to schedule a ride to my doctor?
>
**Bot said:**

```
I don't have that information. Please call Med-QUEST at 1-800-316-8005.

They can tell you the specific scheduling requirements for medical transportation services.
```

- Missing: 48
- Told the person to call although the site answers this
- Expected: At least 48 hours before the appointment, through your health plan; urgent visits within 24 hours can be booked with less notice.
- Source: https://medquest.hawaii.gov/en/members-applicants/quest-integration-coverage/nemt

### ho-ride-cost (Held-out) run 1

- Grader: fail, correct 2, complete 0: Fails to give the site's answer that a covered NEMT ride costs nothing, and sends the person to call Med-QUEST instead of their health plan, which arranges rides.

> **Q:** Do I have to pay for a Medicaid ride?
>
**Bot said:**

```
I don't have that information. Please call Med-QUEST at 1-800-316-8005.

They can answer your question about whether you pay for transportation services covered by Medicaid.
```

- Missing: no cost / free / no charge / no extra charge / don't have to pay / do not have to pay
- Told the person to call although the site answers this
- Expected: No: a covered Non-Emergency Medical Transportation ride costs nothing.
- Source: https://medquest.hawaii.gov/en/members-applicants/quest-integration-coverage/nemt

### ho-ride-cost (Held-out) run 2

- Grader: fail, correct 2, complete 0: The bot said it lacked the information, but the site states a covered NEMT ride costs nothing; it sent the person to call instead of answering.

> **Q:** Do I have to pay for a Medicaid ride?
>
**Bot said:**

```
I don't have that information. Please call Med-QUEST at 1-800-316-8005.

They can answer questions about transportation benefits and any associated costs.
```

- Missing: no cost / free / no charge / no extra charge / don't have to pay / do not have to pay
- Told the person to call although the site answers this
- Expected: No: a covered Non-Emergency Medical Transportation ride costs nothing.
- Source: https://medquest.hawaii.gov/en/members-applicants/quest-integration-coverage/nemt

### ho-cwip (Held-out) run 1

> **Q:** What is the Hawaii Child Wellness Incentive Program and how do I apply?
>
**Bot said:**

```
# Hawaii Child Wellness Incentive Pilot Program (HCWIP)

## What It Is
The program awards a **$50 gift card** to parents who are Medicaid/QUEST beneficiaries when their child completes a well-child examination. You can receive one gift card per child, per year.

The goal is to ensure children's health and support early detection of potential illnesses.

## How to Apply

1. Your child must have a **well-child examination** completed by a licensed health care professional.

2. After the exam, complete the **DHS 1193 form** (Hawaii Child Wellness Incentive Pilot Program Application).

3. The licensed health care professional who performed the exam must also complete their section of the form and certify the information.

4. Submit the completed form to Med-QUEST.

## Requirements
- You must be a Medicaid/QUEST beneficiary
- Your child must have completed a well-child examination as required by the Hawaii Child Wellness Program

For questions or to get the form, contact Med-QUEST at **1-800-316-8005** or visit the website for a fillable version of the DHS 1193 form.
```

- Missing: mydhs / Hawaii_CWIP / email / HCWIP@dhs.hawaii.gov
- Told the person to call although the site answers this
- Expected: A pilot paying parents on Medicaid $50 for each child's yearly well-child exam (children under 18). Steps: take the child for the exam, have the doctor complete section 2 of Form DHS 1193, then submit it through the program's web page or the MyDHS portal (mydhs.hawaii.gov), by email to HCWIP@dhs.hawaii.gov, by fax to 808-900-7978, or by mail. The card arrives in 4-6 weeks.
- Source: https://medquest.hawaii.gov/en/members-applicants/already-covered/Hawaii_CWIP

### ho-cwip (Held-out) run 2

> **Q:** What is the Hawaii Child Wellness Incentive Program and how do I apply?
>
**Bot said:**

```
## Hawaii Child Wellness Incentive Pilot Program (HCWIP)

**What it is:**
The HCWIP awards a **$50 gift card** to Medicaid/QUEST beneficiary parents for each child who completes a well-child examination once per year. The program is designed to ensure children's health and enable early detection of potential illnesses.

**How to apply:**

1. **Have your child complete a well-child examination** with a licensed health care professional.

2. **Complete the DHS 1193 form** ("Hawai'i Child Wellness Incentive Pilot Program (HCWIP) Application").

3. **Your child's health care provider** will need to certify on the form that the well-child examination was completed.

4. **Submit the completed form** to Med-QUEST.

**Who qualifies:**
- You must be a Medicaid/QUEST beneficiary parent
- Your child must have completed a well-child examination

For more details or to get the form, contact Med-QUEST at **1-800-316-8005** or visit the Med-QUEST website.
```

- Missing: mydhs / Hawaii_CWIP / email / HCWIP@dhs.hawaii.gov
- Told the person to call although the site answers this
- Expected: A pilot paying parents on Medicaid $50 for each child's yearly well-child exam (children under 18). Steps: take the child for the exam, have the doctor complete section 2 of Form DHS 1193, then submit it through the program's web page or the MyDHS portal (mydhs.hawaii.gov), by email to HCWIP@dhs.hawaii.gov, by fax to 808-900-7978, or by mail. The card arrives in 4-6 weeks.
- Source: https://medquest.hawaii.gov/en/members-applicants/already-covered/Hawaii_CWIP

### ho-help-applying (Held-out) run 1

- Grader: fail, correct 0, complete 1: Cites 'Certified Application Counselors' and an 'Appendix C', neither on the site, and omits the community partners page that offers application help.

> **Q:** Is there someone who can help me fill out my application?
>
**Bot said:**

```
Yes. Help is available:

**Free assistance from the Department:**
- Med-QUEST staff can help you in person, over the phone, or online
- Services are accessible for people with disabilities and those who need language interpretation

**Certified Application Counselors:**
- The Department has certified application counselors who can assist with:
  - Completing and submitting your application
  - Contacting the Department about your application status
  - Helping you respond to the Department
- Their services are provided free of charge

**Authorized Representatives:**
- You can authorize someone to help you fill out and sign your application
- They'll need to complete Appendix C with your permission

**To get started:**
- Apply online through KOLEA, or
- Call Med-QUEST at **1-800-316-8005** to apply and get connected with assistance

Free interpreter services are also available if you need them in another language.
```

- Expected: Community partners can help with applications; you can also call 1-800-316-8005 or visit an eligibility office.
- Source: https://medquest.hawaii.gov/en/members-applicants/member-resources

### ho-help-applying (Held-out) run 2

- Grader: fail, correct 0, complete 1: The answer cites an 'Appendix C' supplemental form and counselor duties like case management that the site doesn't support, and it omits the community partners page.

> **Q:** Is there someone who can help me fill out my application?
>
**Bot said:**

```
Yes. Med-QUEST provides free assistance to help you complete your application:

**In-person, by phone, or online:**
The Department provides assistance directly through all three methods.

**Certified Application Counselors:**
Med-QUEST has certified application counselors who can help you for free. They can:
- Complete or submit your application
- Interact with the Department about your application status
- Help you respond to the Department
- Provide case management after approval

**Authorized Representative:**
You can also authorize someone to fill out the application on your behalf. They must complete a supplemental form (Appendix C) with your permission.

**To get started:**
- Apply online through KOLEA, or
- Call Med-QUEST at **1-800-316-8005**

They can connect you with an application counselor or provide other assistance you need.
```

- Expected: Community partners can help with applications; you can also call 1-800-316-8005 or visit an eligibility office.
- Source: https://medquest.hawaii.gov/en/members-applicants/member-resources

### ho-hearing (Held-out) run 1

- Grader: fail, correct 2, complete 0: Says it lacks the information, but the site lists vision and hearing services as covered QUEST Integration benefits; it sends the person to call instead of answering.

> **Q:** Are hearing tests covered?
>
**Bot said:**

```
I don't have that information. Please call Med-QUEST at 1-800-316-8005.

They can tell you what hearing-related services are covered under your Med-QUEST plan.
```

- Told the person to call although the site answers this
- Expected: Yes: vision and hearing services are covered QUEST Integration benefits; check details with your health plan.
- Source: https://medquest.hawaii.gov/en/members-applicants/quest-integration-coverage/medical-benefits

### ho-hearing (Held-out) run 2

- Grader: fail, correct 2, complete 0: The bot says it lacks the information, but the site lists vision and hearing services as covered QUEST Integration benefits, so it sends the person to call needlessly.

> **Q:** Are hearing tests covered?
>
**Bot said:**

```
I don't have that information. Please call Med-QUEST at 1-800-316-8005.

They can tell you what hearing services and tests are covered under your Med-QUEST plan.
```

- Told the person to call although the site answers this
- Expected: Yes: vision and hearing services are covered QUEST Integration benefits; check details with your health plan.
- Source: https://medquest.hawaii.gov/en/members-applicants/quest-integration-coverage/medical-benefits

### ho-foster (Held-out) run 1

> **Q:** I aged out of foster care and I'm 22 now. Can I still get Medicaid?
>
**Bot said:**

```
Yes, you may still qualify. People who age out of foster care can be eligible for a "former foster care" eligibility group.

To find out if you qualify, you need to apply. Applying is free and you can:

- Apply online through KOLEA, or
- Call Med-QUEST at 1-800-316-8005

Med-QUEST can also answer specific questions about your situation.
```

- Missing: 26
- Told the person to call although the site answers this
- Expected: Yes, likely: Med-QUEST covers certain former foster care youth from 18 up to age 26. Apply to confirm.
- Source: https://medquest.hawaii.gov/en/members-applicants/get-started/programs

### ho-foster (Held-out) run 2

- Grader: fail, correct 1, complete 1: It says eligibility depends on income and household size, which the site does not state for former foster youth, and it leaves out that coverage runs up to age 26.

> **Q:** I aged out of foster care and I'm 22 now. Can I still get Medicaid?
>
**Bot said:**

```
Yes, you may qualify for Medicaid as a former foster care youth.

There is a "former foster care" eligibility group for people who aged out of foster care. Your eligibility will depend on factors like your income and household size.

The only way to know for sure if you qualify is to apply. It's free.

**Apply:**
- Online through KOLEA, or
- Call Med-QUEST at 1-800-316-8005

They can answer questions about your specific situation and help you apply.
```

- Missing: 26
- Told the person to call although the site answers this
- Expected: Yes, likely: Med-QUEST covers certain former foster care youth from 18 up to age 26. Apply to confirm.
- Source: https://medquest.hawaii.gov/en/members-applicants/get-started/programs

### ho-handbook (Held-out) run 1

> **Q:** Where can I find the QUEST member handbook?
>
**Bot said:**

```
You can find the QUEST Member Handbook on the Med-QUEST website. Look for "Member Handbook" in the Members & Applicants section under "Get Started."

You can also contact your health plan directly—they'll mail you a welcome packet after you enroll that includes important information about your coverage.

If you need help locating it, call Med-QUEST at 1-800-316-8005.
```

- Told the person to call although the site answers this
- Expected: On the member resources / member handbook pages: the 2025 QUEST Member Handbook, plus each health plan's own handbook.
- Source: https://medquest.hawaii.gov/en/members-applicants/member-resources

### ho-handbook (Held-out) run 2

> **Q:** Where can I find the QUEST member handbook?
>
**Bot said:**

```
You can find the QUEST Member Handbook on the Med-QUEST website. Look for "Member Handbook" in the "Get Started" section under "Members & Applicants."

You can also contact your health plan directly for a copy. Your health plan will mail you a welcome packet after you enroll, which includes important information about your coverage.

If you need help locating it, call Med-QUEST at 1-800-316-8005.
```

- Told the person to call although the site answers this
- Expected: On the member resources / member handbook pages: the 2025 QUEST Member Handbook, plus each health plan's own handbook.
- Source: https://medquest.hawaii.gov/en/members-applicants/member-resources

### ho-toothache (Held-out) run 1

> **Q:** I have a really bad toothache. Is emergency dental covered for adults?
>
**Bot said:**

```
Yes. If you're age 21 or older, **emergency and palliative treatment** is covered.

To find a dentist who accepts Medicaid, call:
- **Oʻahu:** 808-792-1070
- **Neighbor Islands:** 1-888-792-1070 (toll-free)

Present your Medicaid ID card to the dentist.

If you need immediate assistance, you can also call Med-QUEST at **1-800-316-8005**.
```

- Told the person to call although the site answers this
- Expected: Yes: for adults 21 and older, emergency and palliative dental treatment is covered. Call CCMC to find a dentist (O'ahu 808-792-1070, neighbor islands 1-888-792-1070).
- Source: https://medquest.hawaii.gov/en/members-applicants/quest-integration-coverage/Dental

### ho-pidgin-renew (Held-out) run 1

- Grader: fail, correct 1, complete 2: Unsupported claim that the form goes to the address on page 1 (site says mail or fax it to the nearest Eligibility Office), TTY 711 is mislabeled as interpreter help, and there is no link to the online portal.

> **Q:** Eh how I renew my Med-QUEST? I wen get one pink letter
>
**Bot said:**

```
Eh, da pink letter stay your renewal notice. Get few ways fo renew:

**Online:**
- Go KOLEA website

**By phone:**
- Call Med-QUEST Customer Service: **1-800-316-8005**
- Can do da whole renewal ting over da phone
- Get interpreter help if need: TTY/TDD **711**

**By mail:**
- Fill out da form from da pink letter
- Send back to address on page 1 of da form

**In person:**
- Go one Eligibility Branch Office (get one near you)

Da pink letter get all da info you stay need. Stay follow da instructions stay on top da letter.

Any question about da renewal, call **1-800-316-8005**.
```

- Expected: Renew online at medical.mybenefits.hawaii.gov, with the form that came with the pink letter, or by phone at 1-800-316-8005.
- Source: https://medquest.hawaii.gov/en/members-applicants/already-covered/medicaid-renewal-info

### ho-pidgin-renew (Held-out) run 2

- Grader: fail, correct 0, complete 2: The mailing address P.O. Box 3490, Honolulu, HI 96811-3490 appears nowhere on the site, and the online option gives no link to medical.mybenefits.hawaii.gov.

> **Q:** Eh how I renew my Med-QUEST? I wen get one pink letter
>
**Bot said:**

```
Shoots! Here stay da ways fo renew:

**Online:**
- Go KOLEA website

**By phone:**
- Call Med-QUEST Customer Service: **1-800-316-8005**
- (TTY/TDD: 711)
- Stay can complete da renewal ova da phone

**By mail:**
- Return da pink letter (da renewal form) to da address stay on top of page 1
- Or send to: P.O. Box 3490, Honolulu, HI 96811-3490

**In person:**
- Go one Eligibility Branch Office near you

Da easiest stay call 1-800-316-8005 o go online KOLEA. Get any questions, da folks stay stay help you.
```

- Expected: Renew online at medical.mybenefits.hawaii.gov, with the form that came with the pink letter, or by phone at 1-800-316-8005.
- Source: https://medquest.hawaii.gov/en/members-applicants/already-covered/medicaid-renewal-info

### ho-follow-fraud (Held-out) run 1

- Grader: fail, correct 2, complete 0: The site lists 1-855-973-1852 as AlohaCare's fraud hotline, but the bot said it lacked the information, referred to 'documents', and sent the person to call instead.

> **Q:** Which health plans can I pick from?
>
> **Q:** Which one of those has the fraud hotline 1-855-973-1852?
>
**Bot said:**

```
I don't have that information in the documents provided. Please call Med-QUEST at 1-800-316-8005, and they can tell you which health plan operates that fraud hotline.
```

- Missing: AlohaCare / Aloha Care
- Told the person to call although the site answers this
- Expected: AlohaCare's 24/7 fraud reporting hotline is 1-855-973-1852.
- Source: https://medquest.hawaii.gov/en/members-applicants/fraud-prevention

### ho-follow-fraud (Held-out) run 2

- Grader: fail, correct 2, complete 0: The bot said it didn't have the answer and mentioned 'documents', but the site's fraud prevention page lists 1-855-973-1852 as AlohaCare's 24/7 fraud hotline.

> **Q:** Which health plans can I pick from?
>
> **Q:** Which one of those has the fraud hotline 1-855-973-1852?
>
**Bot said:**

```
I don't have that information in the documents provided. Please call Med-QUEST at 1-800-316-8005, and they can tell you which health plan has that fraud hotline number.
```

- Missing: AlohaCare / Aloha Care
- Told the person to call although the site answers this
- Expected: AlohaCare's 24/7 fraud reporting hotline is 1-855-973-1852.
- Source: https://medquest.hawaii.gov/en/members-applicants/fraud-prevention

### ho-rehab (Held-out) run 1

- Grader: fail, correct 2, complete 0: The bot said it had no information, but the site lists alcohol and chemical dependency services and substance abuse treatment as covered behavioral health benefits.

> **Q:** Does Med-QUEST pay for drug or alcohol rehab?
>
**Bot said:**

```
I don't have that information. Please call Med-QUEST at 1-800-316-8005. They can tell you what substance use treatment services are covered.
```

- Told the person to call although the site answers this
- Expected: Yes: medically necessary alcohol and chemical dependency services and substance abuse treatment are covered behavioral health services.
- Source: https://medquest.hawaii.gov/en/members-applicants/quest-integration-coverage/medical-benefits

### ho-rehab (Held-out) run 2

- Grader: fail, correct 2, complete 0: The bot said it had no information and sent the person to call, but the site lists medically necessary alcohol and chemical dependency services and substance abuse treatment as covered.

> **Q:** Does Med-QUEST pay for drug or alcohol rehab?
>
**Bot said:**

```
I don't have that information. Please call Med-QUEST at 1-800-316-8005. They can tell you what substance abuse treatment services are covered.
```

- Told the person to call although the site answers this
- Expected: Yes: medically necessary alcohol and chemical dependency services and substance abuse treatment are covered behavioral health services.
- Source: https://medquest.hawaii.gov/en/members-applicants/quest-integration-coverage/medical-benefits

### ho-moving-away (Held-out) run 1

- Grader: fail, correct 1, complete 2: It claims Med-QUEST will give information on applying for Medicaid in California, which the site does not support.

> **Q:** I'm moving to California next month. What happens to my Med-QUEST?
>
**Bot said:**

```
Med-QUEST is Hawaii's Medicaid program and only covers residents of Hawaii.

When you move to California, you'll need to apply for Medicaid in California. Each state has its own Medicaid program with different eligibility rules and benefits.

Before you move, contact Med-QUEST at **1-800-316-8005** to:
- Report your address change and move date
- Learn about next steps for your coverage

They can also provide information about how to apply for Medicaid in California.
```

- Expected: Report the move (change of address) to Med-QUEST; Med-QUEST covers Hawai'i residents, so apply for Medicaid in the new state.
- Source: https://medquest.hawaii.gov/en/faq
