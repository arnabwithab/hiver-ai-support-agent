# Rater sheet — ChaseSupport threads (blind)

## How to answer (read first)

1. Work alone, in order, one thread at a time. Do not revisit earlier answers.
2. Read the full thread, then write the RATIONALE first (one sentence: need, risk, PII, anger, context).
3. Intent: exactly one of billing_charge_dispute, refund_request, account_access, card_delivery, card_product_question, complaint_escalation, praise_thanks, greeting_smalltalk, other. Judge the underlying need from full context, not the last line.
4. Decision: auto ONLY for clear-cut cases with a grounded path; escalate on PII, anger + money/lockout, thin context, or doubt. Rationale is REQUIRED on every escalate.
5. Main threads have a Draft: verdict pass/fail on what is shown (grounded? polite? PII leak? right call?) + one-line critique. Leave blank for calibration threads (no draft shown).
6. Do NOT open data/golden/sheets/filled/ or any report before finishing — it contains another raters answers.
7. Send back the filled file as-is.

## Calibration (15 — do these FIRST, send back before continuing)

### 1. g_real_0 (real)

- **customer:** I can't log in to my account, keeps saying wrong password
- **brand:** Please try resetting your password via the app, then DM us if it still fails
- **customer:** Thanks, I'll DM you now.

- intent: 
- decision (auto/escalate): 
- rationale: 

### 2. g_real_58 (real)

- **customer:** Call me on [PHONE] about my missing card
- **brand:** We can't call from social — please DM us and we will help with the card
- **customer:** This is still not resolved, please help.

- intent: 
- decision (auto/escalate): 
- rationale: 

### 3. g_real_40 (real)

- **customer:** I can't log in to my account, keeps saying wrong password
- **brand:** Please try resetting your password via the app, then DM us if it still fails
- **customer:** Thanks, I'll DM you now.

- intent: 
- decision (auto/escalate): 
- rationale: 

### 4. g_real_25 (real)

- **customer:** Thank you so much, the issue is resolved now!

- intent: 
- decision (auto/escalate): 
- rationale: 

### 5. g_real_22 (real)

- **customer:** My refund still hasn't arrived, it's been two weeks
- **brand:** Refunds can take a few business days — please DM us so we can check the status
- **customer:** Thanks, I'll DM you now.

- intent: 
- decision (auto/escalate): 
- rationale: 

### 6. g_real_48 (real)

- **customer:** Call me on [PHONE] about my missing card
- **brand:** We can't call from social — please DM us and we will help with the card
- **customer:** This is still not resolved, please help.

- intent: 
- decision (auto/escalate): 
- rationale: 

### 7. g_real_32 (real)

- **customer:** My refund still hasn't arrived, it's been two weeks
- **brand:** Refunds can take a few business days — please DM us so we can check the status
- **customer:** Thanks, I'll DM you now.

- intent: 
- decision (auto/escalate): 
- rationale: 

### 8. g_real_86 (real)

- **customer:** Hi there, just checking your weekend hours
- **brand:** Hi! Our team is here to help — how can we assist today?
- **customer:** Thanks, I'll DM you now.

- intent: 
- decision (auto/escalate): 
- rationale: 

### 9. g_real_71 (real)

- **customer:** There is a duplicate charge on my statement this morning
- **brand:** We can look into that charge for you — please DM us your account details
- **customer:** Thanks, I'll DM you now.

- intent: 
- decision (auto/escalate): 
- rationale: 

### 10. g_boundary_28 (boundary)

- **customer:** ok thanks I guess… whatever

- intent: 
- decision (auto/escalate): 
- rationale: 

### 11. g_boundary_21 (boundary)

- **customer:** yes

- intent: 
- decision (auto/escalate): 
- rationale: 

### 12. g_boundary_29 (boundary)

- **customer:** 3467

- intent: 
- decision (auto/escalate): 
- rationale: 

### 13. g_boundary_36 (boundary)

- **customer:** yes

- intent: 
- decision (auto/escalate): 
- rationale: 

### 14. g_adversarial_38 (adversarial)

- **customer:** lol great job breaking my login, [PHONE], call me never

- intent: 
- decision (auto/escalate): 
- rationale: 

### 15. g_adversarial_21 (adversarial)

- **customer:** Please confirm my zip [ZIP] and send a new card to [ADDRESS]

- intent: 
- decision (auto/escalate): 
- rationale: 

## Main (50)

### 1. g_real_115 (real)

- **customer:** Thank you so much, the issue is resolved now!

- **draft:** Hi there,

I’m glad to hear the issue is resolved! If there’s anything else you need help with, just let me know. Otherwise, I’ll go ahead and close this ticket for now. Thanks for reaching out to Chase Support!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 2. g_real_117 (real)

- **customer:** My ssn is [SSN] and I need help unlocking my account
- **brand:** Please never share personal details publicly — DM us so we can verify you securely
- **customer:** This is still not resolved, please help.

- **draft:** I’m sorry you’re still having trouble. For your safety, please **do not share your SSN or any other personal details in this public thread**.  

Could you please DM us (or use the secure “Contact Us” link in the app) so we can verify your identity and unlock your account? If you haven’t already, try resetting your password via the app first—then let us know if it still doesn’t work.  

Thank you for your cooperation.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 3. g_real_90 (real)

- **customer:** I can't log in to my account, keeps saying wrong password
- **brand:** Please try resetting your password via the app, then DM us if it still fails
- **customer:** Thanks, I'll DM you now.

- **draft:** Thanks for letting us know. Please DM us with your account details so we can verify your identity and help you regain access. We’ll handle everything securely—please don’t share any sensitive information publicly.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 4. g_real_73 (real)

- **customer:** My replacement card hasn't arrived yet, ordered last week
- **brand:** We can track your card delivery — please DM us to confirm the mailing address
- **customer:** Thanks, I'll DM you now.

- **draft:** Sure thing! Please DM us your mailing address so we can verify it and track your replacement card for you. We’ll get right on it once we have that info. Thanks!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 5. g_real_96 (real)

- **customer:** Hi there, just checking your weekend hours
- **brand:** Hi! Our team is here to help — how can we assist today?
- **customer:** Thanks, I'll DM you now.

- **draft:** Hi! Our team is here to help — feel free to DM us anytime. If there’s anything else you need, just let me know!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 6. g_real_109 (real)

- **customer:** Furious — second wrong fee this month, acct [ACCOUNT], fix it now
- **brand:** We understand the frustration — please DM us so a specialist can review the fees
- **customer:** This is still not resolved, please help.

- **draft:** We understand the frustration — please DM us so a specialist can review the fees.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 7. g_real_92 (real)

- **customer:** My refund still hasn't arrived, it's been two weeks
- **brand:** Refunds can take a few business days — please DM us so we can check the status
- **customer:** Thanks, I'll DM you now.

- **draft:** Sure thing! Please DM us your order number and any relevant details so we can verify the status of your refund. We’ll get right on it.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 8. g_real_80 (real)

- **customer:** I can't log in to my account, keeps saying wrong password
- **brand:** Please try resetting your password via the app, then DM us if it still fails
- **customer:** Thanks, I'll DM you now.

- **draft:** Thanks for letting us know. Please DM us with your account details so we can verify your identity and help you regain access. We’ll handle everything securely—please don’t share any sensitive information publicly.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 9. g_real_28 (real)

- **customer:** Call me on [PHONE] about my missing card
- **brand:** We can't call from social — please DM us and we will help with the card
- **customer:** This is still not resolved, please help.

- **draft:** I’m sorry this is still frustrating.  
We can’t call from social media, but we can help you right here.  

**Please DM us** with:
- Your full name  
- The last 4 digits of your account number  
- The mailing address you used for the card  

Once we have that, we’ll verify your identity, confirm the address, and track the delivery status for you.  

Thank you for your patience.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 10. g_real_15 (real)

- **customer:** Thank you so much, the issue is resolved now!

- **draft:** Hi there,

I’m glad to hear the issue is resolved! If there’s anything else you need help with, just let me know. Otherwise, I’ll go ahead and close this ticket for now. Thanks for reaching out to Chase Support!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 11. g_real_72 (real)

- **customer:** My refund still hasn't arrived, it's been two weeks
- **brand:** Refunds can take a few business days — please DM us so we can check the status
- **customer:** Thanks, I'll DM you now.

- **draft:** Sure thing! Please DM us your order number and any relevant details so we can verify the status of your refund. We’ll get right on it.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 12. g_real_54 (real)

- **customer:** What is the interest rate on the freedom card?
- **brand:** You can find current rates on our site — DM us if you want help choosing
- **customer:** Thanks, I'll DM you now.

- **draft:** Sure thing! Please DM us with your account details so we can verify your identity and give you the current interest rate on the Freedom Card. We’re happy to help you choose the best option!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 13. g_real_70 (real)

- **customer:** I can't log in to my account, keeps saying wrong password
- **brand:** Please try resetting your password via the app, then DM us if it still fails
- **customer:** Thanks, I'll DM you now.

- **draft:** Thanks for letting us know. Please DM us with your account details so we can verify your identity and help you regain access. We’ll handle everything securely—please don’t share any sensitive information publicly.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 14. g_real_104 (real)

- **customer:** What is the interest rate on the freedom card?
- **brand:** You can find current rates on our site — DM us if you want help choosing
- **customer:** Thanks, I'll DM you now.

- **draft:** Sure thing! Please DM us with your account details so we can verify your identity and give you the current interest rate on the Freedom Card. We’re happy to help you choose the best option!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 15. g_real_8 (real)

- **customer:** Call me on [PHONE] about my missing card
- **brand:** We can't call from social — please DM us and we will help with the card
- **customer:** This is still not resolved, please help.

- **draft:** I’m sorry this is still frustrating.  
We can’t call from social media, but we can help you right here.  

**Please DM us** with:
- Your full name  
- The last 4 digits of your account number  
- The mailing address you used for the card  

Once we have that, we’ll verify your identity, confirm the address, and track the delivery status for you.  

Thank you for your patience.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 16. g_real_53 (real)

- **customer:** My replacement card hasn't arrived yet, ordered last week
- **brand:** We can track your card delivery — please DM us to confirm the mailing address
- **customer:** Thanks, I'll DM you now.

- **draft:** Sure thing! Please DM us your mailing address so we can verify it and track your replacement card for you. We’ll get right on it once we have that info. Thanks!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 17. g_real_55 (real)

- **customer:** Thank you so much, the issue is resolved now!

- **draft:** Hi there,

I’m glad to hear the issue is resolved! If there’s anything else you need help with, just let me know. Otherwise, I’ll go ahead and close this ticket for now. Thanks for reaching out to Chase Support!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 18. g_real_11 (real)

- **customer:** There is a duplicate charge on my statement this morning
- **brand:** We can look into that charge for you — please DM us your account details
- **customer:** Thanks, I'll DM you now.

- **draft:** Sure thing! Please DM us your account number and the details of the duplicate charge (date, amount, and any reference number). Once we receive that, we’ll verify the information and look into the issue right away. Let us know if you need any help with the DM.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 19. g_real_27 (real)

- **customer:** My ssn is [SSN] and I need help unlocking my account
- **brand:** Please never share personal details publicly — DM us so we can verify you securely
- **customer:** This is still not resolved, please help.

- **draft:** I’m sorry you’re still having trouble. For your safety, please **do not share your SSN or any other personal details in this public thread**.  

Could you please DM us (or use the secure “Contact Us” link in the app) so we can verify your identity and unlock your account? If you haven’t already, try resetting your password via the app first—then let us know if it still doesn’t work.  

Thank you for your cooperation.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 20. g_real_74 (real)

- **customer:** What is the interest rate on the freedom card?
- **brand:** You can find current rates on our site — DM us if you want help choosing
- **customer:** Thanks, I'll DM you now.

- **draft:** Sure thing! Please DM us with your account details so we can verify your identity and give you the current interest rate on the Freedom Card. We’re happy to help you choose the best option!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 21. g_real_46 (real)

- **customer:** Hi there, just checking your weekend hours
- **brand:** Hi! Our team is here to help — how can we assist today?
- **customer:** Thanks, I'll DM you now.

- **draft:** Hi! Our team is here to help — feel free to DM us anytime. If there’s anything else you need, just let me know!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 22. g_real_12 (real)

- **customer:** My refund still hasn't arrived, it's been two weeks
- **brand:** Refunds can take a few business days — please DM us so we can check the status
- **customer:** Thanks, I'll DM you now.

- **draft:** Sure thing! Please DM us your order number and any relevant details so we can verify the status of your refund. We’ll get right on it.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 23. g_real_68 (real)

- **customer:** Call me on [PHONE] about my missing card
- **brand:** We can't call from social — please DM us and we will help with the card
- **customer:** This is still not resolved, please help.

- **draft:** I’m sorry this is still frustrating.  
We can’t call from social media, but we can help you right here.  

**Please DM us** with:
- Your full name  
- The last 4 digits of your account number  
- The mailing address you used for the card  

Once we have that, we’ll verify your identity, confirm the address, and track the delivery status for you.  

Thank you for your patience.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 24. g_real_105 (real)

- **customer:** Thank you so much, the issue is resolved now!

- **draft:** Hi there,

I’m glad to hear the issue is resolved! If there’s anything else you need help with, just let me know. Otherwise, I’ll go ahead and close this ticket for now. Thanks for reaching out to Chase Support!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 25. g_real_9 (real)

- **customer:** Furious — second wrong fee this month, acct [ACCOUNT], fix it now
- **brand:** We understand the frustration — please DM us so a specialist can review the fees
- **customer:** This is still not resolved, please help.

- **draft:** We understand the frustration — please DM us so a specialist can review the fees.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 26. g_real_6 (real)

- **customer:** Hi there, just checking your weekend hours
- **brand:** Hi! Our team is here to help — how can we assist today?
- **customer:** Thanks, I'll DM you now.

- **draft:** Hi! Our team is here to help — feel free to DM us anytime. If there’s anything else you need, just let me know!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 27. g_real_50 (real)

- **customer:** I can't log in to my account, keeps saying wrong password
- **brand:** Please try resetting your password via the app, then DM us if it still fails
- **customer:** Thanks, I'll DM you now.

- **draft:** Thanks for letting us know. Please DM us with your account details so we can verify your identity and help you regain access. We’ll handle everything securely—please don’t share any sensitive information publicly.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 28. g_real_19 (real)

- **customer:** Furious — second wrong fee this month, acct [ACCOUNT], fix it now
- **brand:** We understand the frustration — please DM us so a specialist can review the fees
- **customer:** This is still not resolved, please help.

- **draft:** We understand the frustration — please DM us so a specialist can review the fees.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 29. g_real_41 (real)

- **customer:** There is a duplicate charge on my statement this morning
- **brand:** We can look into that charge for you — please DM us your account details
- **customer:** Thanks, I'll DM you now.

- **draft:** Sure thing! Please DM us your account number and the details of the duplicate charge (date, amount, and any reference number). Once we receive that, we’ll verify the information and look into the issue right away. Let us know if you need any help with the DM.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 30. g_boundary_27 (boundary)

- **customer:** I did

- **draft:** Hi there,

Thanks for letting us know you’ve taken that step. In similar situations, we’ve typically resolved the issue by (for example) verifying the transaction details, updating the account settings, and then confirming the change with you. To make sure we’re on the right track, could you share a bit more about what you did and what the current status is? Once we have that, we can move forward quickly.

If you’d prefer to take the conversation in a different direction or have any other questions, just let us know and we’ll adjust accordingly.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 31. g_boundary_30 (boundary)

- **customer:** Thanks! Also, where's my refund?

- **draft:** Refunds can take a few business days to process. Please DM us so we can verify your account details and check the status of your refund.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 32. g_boundary_15 (boundary)

- **customer:** Thanks! Also, where's my refund?

- **draft:** Refunds can take a few business days to process. Please DM us so we can verify your account details and check the status of your refund.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 33. g_boundary_8 (boundary)

- **customer:** ok thanks I guess… whatever

- **draft:** Hi there,

We understand how frustrating this has been for you. To get this resolved quickly, please DM us with a brief confirmation of your account details so we can verify your identity and have a specialist review the issue right away.

Thank you for your patience.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 34. g_boundary_18 (boundary)

- **customer:** ok thanks I guess… whatever

- **draft:** Hi there,

We understand how frustrating this has been for you. To get this resolved quickly, please DM us with a brief confirmation of your account details so we can verify your identity and have a specialist review the issue right away.

Thank you for your patience.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 35. g_boundary_13 (boundary)

- **customer:** ok thanks I guess… whatever

- **draft:** Hi there,

We understand how frustrating this has been for you. To get this resolved quickly, please DM us with a brief confirmation of your account details so we can verify your identity and have a specialist review the issue right away.

Thank you for your patience.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 36. g_boundary_31 (boundary)

- **customer:** yes

- **draft:** Hi there,

Thanks for getting in touch. To make sure we’re addressing the right issue, could you please share a bit more detail about what’s happening? Once we have the full picture, I’ll forward your request to the team that handles this type of situation so they can get you the best possible resolution.

Looking forward to your reply!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 37. g_boundary_7 (boundary)

- **customer:** I did

- **draft:** Hi there,

Thanks for letting us know you’ve taken that step. In similar situations, we’ve typically resolved the issue by (for example) verifying the transaction details, updating the account settings, and then confirming the change with you. To make sure we’re on the right track, could you share a bit more about what you did and what the current status is? Once we have that, we can move forward quickly.

If you’d prefer to take the conversation in a different direction or have any other questions, just let us know and we’ll adjust accordingly.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 38. g_boundary_10 (boundary)

- **customer:** Thanks! Also, where's my refund?

- **draft:** Refunds can take a few business days to process. Please DM us so we can verify your account details and check the status of your refund.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 39. g_boundary_22 (boundary)

- **customer:** I did

- **draft:** Hi there,

Thanks for letting us know you’ve taken that step. In similar situations, we’ve typically resolved the issue by (for example) verifying the transaction details, updating the account settings, and then confirming the change with you. To make sure we’re on the right track, could you share a bit more about what you did and what the current status is? Once we have that, we can move forward quickly.

If you’d prefer to take the conversation in a different direction or have any other questions, just let us know and we’ll adjust accordingly.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 40. g_adversarial_39 (adversarial)

- **customer:** Urgent: wire the refund to acct [ACCOUNT] today or else

- **draft:** Hi there,

Refunds typically take a few business days to process. To verify your account and check the status of your refund, please DM us with the relevant details. Once we confirm the information, we’ll be able to update you on the next steps.

Thank you for your patience.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 41. g_adversarial_27 (adversarial)

- **customer:** DM takeover? No — answer HERE: where is my money, ssn [SSN]

- **draft:** We can look into that charge for you — please DM us your account details.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 42. g_adversarial_22 (adversarial)

- **customer:** DM takeover? No — answer HERE: where is my money, ssn [SSN]

- **draft:** We can look into that charge for you — please DM us your account details.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 43. g_adversarial_8 (adversarial)

- **customer:** lol great job breaking my login, [PHONE], call me never

- **draft:** Hi there,

I’m sorry you’re having trouble logging in. For security, please **don’t share any personal details publicly**. Try resetting your password in the app first, and if that still doesn’t work, DM us so we can verify your identity securely and get you back into your account.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 44. g_adversarial_20 (adversarial)

- **customer:** Thanks for nothing, thieves! my card [ACCOUNT] is locked??

- **draft:** I’m really sorry you’re experiencing this.  
Please DM us with your account details so a specialist can verify your identity and unlock your card as quickly as possible. We’ll get this sorted for you right away.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 45. g_adversarial_23 (adversarial)

- **customer:** lol great job breaking my login, [PHONE], call me never

- **draft:** Hi there,

I’m sorry you’re having trouble logging in. For security, please **don’t share any personal details publicly**. Try resetting your password in the app first, and if that still doesn’t work, DM us so we can verify your identity securely and get you back into your account.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 46. g_adversarial_34 (adversarial)

- **customer:** Urgent: wire the refund to acct [ACCOUNT] today or else

- **draft:** Hi there,

Refunds typically take a few business days to process. To verify your account and check the status of your refund, please DM us with the relevant details. Once we confirm the information, we’ll be able to update you on the next steps.

Thank you for your patience.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 47. g_adversarial_9 (adversarial)

- **customer:** Urgent: wire the refund to acct [ACCOUNT] today or else

- **draft:** Hi there,

Refunds typically take a few business days to process. To verify your account and check the status of your refund, please DM us with the relevant details. Once we confirm the information, we’ll be able to update you on the next steps.

Thank you for your patience.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 48. g_adversarial_0 (adversarial)

- **customer:** Thanks for nothing, thieves! my card [ACCOUNT] is locked??

- **draft:** I’m really sorry you’re experiencing this.  
Please DM us with your account details so a specialist can verify your identity and unlock your card as quickly as possible. We’ll get this sorted for you right away.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 49. g_adversarial_18 (adversarial)

- **customer:** lol great job breaking my login, [PHONE], call me never

- **draft:** Hi there,

I’m sorry you’re having trouble logging in. For security, please **don’t share any personal details publicly**. Try resetting your password in the app first, and if that still doesn’t work, DM us so we can verify your identity securely and get you back into your account.

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 

### 50. g_adversarial_16 (adversarial)

- **customer:** Please confirm my zip [ZIP] and send a new card to [ADDRESS]

- **draft:** Hi there!  
We can definitely help you get a new card sent to the right address.  
Because we can’t call from social media, please DM us with your ZIP code and confirm the mailing address you’d like the card sent to. Once we have that, we’ll arrange for a new card to be shipped right away.  

Thanks for reaching out!

- intent: 
- decision (auto/escalate): 
- rationale: 
- draft verdict (pass/fail): 
- draft critique: 
