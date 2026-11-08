# Launch checklist (20 items)

The Korean item names are the user's own list (REQ-SKILL-001), in its order. Rule references
point at [sources.md](sources.md); copy the level shown there into the report.

## 1. 개인정보처리방침 (privacy policy)
- How to check: find a link to it on every page that collects data (footer, sign-up, checkout);
  open it and compare with what the code actually collects, why, how long it is kept, who it is
  shared with or outsourced to, and the contact for privacy requests.
- Evidence: the page URL or file, and the collected fields found in forms, APIs and SDKs.
- FAIL signs: no policy; a field or SDK collected but not listed; a template with blanks.
- Rule: S-01.

## 2. 이용약관 (terms of service)
- How to check: a terms page is linked where users sign up or pay, and sign-up shows it before
  agreement.
- Evidence: link location and page.
- FAIL signs: no terms where accounts or payments exist. Whether a clause is fair: NEEDS_HUMAN.
- Rule: S-03.

## 3. 환불정책 (refund policy)
- How to check: when anything is sold, a refund and withdrawal page states the period, how to
  ask, and exceptions; it is reachable before payment.
- Evidence: page, and where checkout links to it.
- FAIL signs: no refund terms for paid goods; a "no refunds" line with no stated legal basis
  (NEEDS_HUMAN for the basis).
- Rule: S-04. N/A when nothing is sold.

## 4. 쿠키정책 (cookie policy)
- How to check: list the cookies, local storage keys and trackers the site sets (code search
  for `document.cookie`, `localStorage`, analytics and ad tags, `Set-Cookie`); a policy page
  names each with its purpose and lifetime.
- Evidence: the list and the page.
- FAIL signs: trackers that no page mentions.
- Rule: S-01 (when a cookie identifies a person), S-20 for EU users.

## 5. 쿠키동의배너 (cookie consent banner)
- How to check: non-essential cookies and trackers are not set before the user chooses; the
  banner offers refusing as easily as accepting; the choice can be changed later.
- Evidence: code path that loads trackers and the condition around it; banner markup.
- FAIL signs: analytics loaded unconditionally; only an "OK" button.
- Rule: S-20 (EU users). For Korean-only users whether a banner is required: NEEDS_HUMAN.

## 6. 입력하는 양식에 동의항목을 확인하기 (consent items on forms)
- How to check: each form that collects personal data shows what is collected, why, how long,
  and that refusing is possible; required and optional consents are separate checkboxes,
  unchecked by default; marketing consent is separate.
- Evidence: form markup and the server-side check that consent was given.
- FAIL signs: one bundled "agree to all" with no separate items; pre-checked boxes.
- Rule: S-02, S-05. N/A when no form collects personal data.

## 7. 불필요한 개인정보는 수집하지 않기 (collect only what is needed)
- How to check: for every collected field, name the feature that needs it.
- Evidence: field list with the feature each one serves.
- FAIL signs: fields no feature uses (birth date, address, ID numbers "just in case").
- Rule: S-06.

## 8. 외부 sdk 점검 (third-party SDKs)
- How to check: list analytics, ads, login, payment, chat and error SDKs (package files, script
  tags); for each, what data it sends and where; each appears in the privacy policy as
  provision to a third party or as outsourcing.
- Evidence: dependency list, network calls or vendor docs, the policy lines.
- FAIL signs: an SDK that sends user data and is not in the policy.
- Rule: S-07, S-08.

## 9. 사용자들이 원하지 않는 선택으로 유도하지 않기 (no dark patterns)
- How to check: cancellation is as easy as sign-up; no pre-selected paid options; no repeated
  pop-ups after "no"; refusing is not hidden or shamed; trial-to-paid is announced.
- Evidence: screens and the code behind them.
- FAIL signs: the patterns above.
- Rule: S-09.

## 10. 숨겨진 요금 없애기 (no hidden fees)
- How to check: the first price shown includes the mandatory fees (shipping, service, tax as
  the market expects); recurring charges show amount and period before payment.
- Evidence: price display code and checkout steps.
- FAIL signs: fees that appear only at the last step.
- Rule: S-09. N/A when nothing is sold.

## 11. 가짜후기 없애기 (no fake reviews)
- How to check: reviews come from real purchases or users; seeded, paid or sponsored reviews
  are labelled; no code generates reviews or ratings.
- Evidence: where reviews come from (data source, admin tools), labels.
- FAIL signs: hard-coded testimonials or ratings shown as real users'.
- Rule: S-10.

## 12. 근거없는 주장 없애기 (no unsupported claims)
- How to check: list claims such as "No. 1", "best", "100%", "proven", health or savings
  figures; each has a source the team can show.
- Evidence: the claim text and its source, or its absence.
- FAIL signs: superlatives or numbers with no source.
- Rule: S-10.

## 13. 접근성을 위한 이미지, 대체 텍스트를 추가 (text alternatives)
- How to check: every informative image, icon button and chart has a text alternative
  (`alt`, `aria-label`); decorative images use `alt=""`.
- Evidence: count of images without alt (code search), examples.
- FAIL signs: missing alt on informative images; icon-only buttons with no label.
- Rule: S-30.

## 14. 글자와 배경에 색상대비를 개선하기 (colour contrast)
- How to check: compute the contrast ratio of text colours against their backgrounds (design
  tokens, CSS); normal text at least 4.5:1, large text at least 3:1.
- Evidence: colour pairs and ratios.
- FAIL signs: grey-on-white body text below 4.5:1; placeholder text used as the only label.
- Rule: S-31.

## 15. 키보드만으로 이동할 수 있게하기 (keyboard access)
- How to check: every control is reachable and usable with Tab, Shift+Tab, Enter and Space;
  the focus outline is visible; no trap; custom widgets have roles and key handlers.
- Evidence: the elements checked, `outline: none` searches, click handlers on non-buttons.
- FAIL signs: `div` click handlers without keyboard support; focus outline removed.
- Rule: S-32, S-33.

## 16. 사업자 정보 추가 (business information)
- How to check: when selling, the site shows the business name, representative, address,
  phone, email, business registration number and mail-order business report number, and the
  terms are reachable.
- Evidence: footer or page.
- FAIL signs: missing items on a selling site. N/A for a free, non-commercial site.
- Rule: S-03.

## 17. 아동의 정보를 수집한다면 나의 관련 수집절차 확인하기 (children's data)
- How to check: whether users under 14 can sign up; if so, a legal guardian's consent step and
  its verification exist; if not, the age gate is stated and enforced.
- Evidence: sign-up flow, age field, guardian flow.
- FAIL signs: no age handling on a service that may reach children.
- Rule: S-11.

## 18. 이메일에 수신거부링크 추가 (unsubscribe link)
- How to check: every advertising email (and SMS or push) template has a working unsubscribe
  link and the sender's identity; unsubscribing takes effect without a login.
- Evidence: templates, the unsubscribe handler.
- FAIL signs: no link; a link that needs login; ads sent without prior opt-in.
- Rule: S-12. N/A when no advertising messages are sent.

## 19. 사용하는 이미지와 글꼴의 이용권을 확보 (image and font licenses)
- How to check: list images, icons, fonts and other assets with their source and license
  file; commercial use and web embedding are allowed by that license.
- Evidence: asset list with license files or purchase records.
- FAIL signs: assets with no known source. Whether a purchased license covers this use:
  NEEDS_HUMAN.
- Rule: S-13.

## 20. 개인정보삭제요청기능 추가 (deletion requests)
- How to check: a user can ask to delete their data (account deletion or a request channel);
  the request reaches data in the database, backups policy, and processors; the result is
  answered within the stated time.
- Evidence: the delete flow and the code that deletes or anonymises.
- FAIL signs: no way to delete; deletion that only hides the account.
- Rule: S-14. N/A when no personal data is kept (no accounts, forms, logs with identifiers).
