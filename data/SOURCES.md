# Seed Data Sources

Provenance and copy guidance for the records in this folder. This file is not loaded by the pipeline. It exists so the evidence behind each athlete-to-business match is kept next to the data without bloating the validated JSON.

## Standing copy rules

- Every ad is interest-based local discovery. The athlete has not endorsed, recommended, or visited any business listed here.
- Allowed: connecting a documented, publicly stated athlete interest to a nearby place a visitor could try, with inspired-by language.
- Prohibited: "recommends", "favorite LA <anything>", "eats at", "trained here", "official partner", or any phrasing that implies a relationship with the business.
- Disclosure line available to the ad prompt: "Interest-based local discovery. Simone Biles has not endorsed or recommended this business."

## simone-biles

- Pepperoni pizza after meets: https://www.teenvogue.com/story/simone-biles-pepperoni-pizza-after-meet-olympics-gymnast
- Sushi, salmon, spicy tuna rolls: https://www.womenshealthmag.com/food/a34482124/simone-biles-diet/ and https://www.elle.com/culture/a34464549/simone-biles-jonathan-van-ness-uber-eats-interview/
- Ice skating during her break from gymnastics: https://people.com/simone-biles-reveals-daring-sport-shes-learning-during-gymnastics-break-exclusive-11847531

## prime-pizza-little-tokyo

- Matches: `italian` cuisine, pepperoni pizza tradition.
- Business info: https://primepizza.com/locations and https://primepizza.com/menu
- Reference photo source: https://primepizza-o5fce583.toast.site/order/prime-pizza-little-tokyo (Toast menu image). Logo source: https://primepizza.com/press
- Demo headline idea: "A big routine calls for a classic slice."

## yama-sushi-marketplace-koreatown

- Matches: `japanese` and `seafood` cuisines, sushi and salmon.
- Business info: https://www.yamasushimarketplace.com/ and https://www.yamasushimarketplace.com/signature-menu
- Reference photo source: https://www.yamasushimarketplace.com/signature-menu. Logo source: the site header or https://www.instagram.com/yamasushimarketplace/
- Demo headline idea: "From a standout routine to standout sushi."

## toyota-sports-performance-center

- Matches: `ice_skating` interest.
- Business info: https://www.toyotasportsperformancecenter.com/ and https://toyotasportsperformancecenter.sportngin.com/page/show/6762512-public-skating
- Reference photo source: https://www.toyotasportsperformancecenter.com/ facility gallery. Logo source: the site header or https://www.instagram.com/lakingstspc/
- Demo headline idea: "Try a different kind of rotation."

## Tagline and offer notes

- All taglines are demo copy written for this project, not the businesses' own slogans.
- On 2026-09-12 the owner requested a ticket-holder promotion for the demo. Yama and Prime Pizza now carry `Demo offer: bring your Olympics ticket for 15% off`. This is explicitly fictional demonstration copy, not a verified or redeemable promotion from either business. Preserve the visible `Demo offer` qualifier in generated ads and judging.
- The sports venue retains null `offer_text`; the ad agent uses its tagline instead. Do not introduce additional promotions.
- Creative direction: connect the observed athletic moment to a documented taste, then invite the visitor to discover it nearby. Example: "Big cheers. Fresh discoveries. Simone loves sushi. Ready to explore your next favorite?" Use Simone Biles's correct name. This clip shows a routine and crowd reaction; do not claim it shows a gold-medal win.
