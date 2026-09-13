# Marketing workspace design system

Concepts: today-concept.png, brand-concept.png, review-concept.png. Generated with the built-in image tool for this project. Main brief: an editorial daily marketing desk for independent cafes/restaurants, complete sidebar, brief composer, brand summary, workflow and review. Brand brief: visual uploads plus editable inferred direction. Review brief: two real ad formats, judge scores and approval. Asset prompts: natural editorial latte in a speckled ceramic cup on a wooden table; sunlit cafe corner with the exact poster text Good Coffee Brighter Days. Both are fictional demonstration assets, not evidence about a real business.

- 252px sidebar; main content 34px padding; 32px header height; 48px gap to title.
- Canvas #F8F6F1; panels white; primary #1C433B; title #101820; muted #787B82; line #E1E3E2; accent #CB6B2B.
- Georgia serif headings: title clamp(38px,4vw,64px), section 28px, item 22px. Arial UI/body 15-16px, helper 14px, lede Georgia 28px.
- Controls 46-54px tall, 7px radius; white panels 10px radius, 1px border, 24px padding; 16px internal gaps and 20px panel gaps.
- Thin 22px outline icons, forest selected navigation, small orange sunrise beside the wordmark.
- Desktop Today split 65/35, Brand split 57/43, Review split 60/40. On mobile, top navigation scrolls and panels stack; primary action remains full width.
- Functional deviations required by real data: empty accounts show setup actions instead of fake brand images; replay selection, optional video choice, upload role/reference selectors, allowance and errors are conditional; actual campaign imagery/copy/scores replace the illustrative concept values. Business/history/settings reuse these component families. External OIDC login uses the configured provider's screen.
- Uploaded assets stay private. Public latte image is used only on the login page and is explicitly a fictional demo asset.
