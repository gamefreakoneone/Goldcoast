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
- `offer_text` is null for every real business because no real promotion exists. The ad agent uses the tagline in place of an offer when `offer_text` is null. Do not invent offers for real businesses.
