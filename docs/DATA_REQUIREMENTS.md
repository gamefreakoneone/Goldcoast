# Data Requirements

Everything the project owner must supply before specs 0001 through 0005 can be validated with real inputs. File paths and field names match the contracts in `TECHNICAL_DESIGN.md`.

## MVP Scope

The MVP is one athlete and one clip, end to end. The athlete is Simone Biles, gymnastics. The goal is to nail the full flow for a single hype moment before adding a second athlete or sport. Everything below is sized for that. Where a section describes multiple clips or athletes, treat it as guidance for later.

Two inputs per run:

- The video clip, from which the video agent picks the hype moment and the hero frame.
- A portrait image of the athlete. It keeps the athlete consistent across both formats, and when the hero frame does not show the face clearly (mid-air, turned away), it is placed as a foreground cutout beside the business's product, with the hero shot as the background.

The ads are framed as discovery, not endorsement. The message is "here is something this athlete is into, and here is where to find it near the venue", never "this athlete recommends this business". Copy is built only from facts in the athlete profile.

Note on a real athlete: Simone Biles is a real public figure. Using her likeness in generated ads is fine for an internal hackathon demo, but the ads must not be published or used commercially without rights, even with the discovery framing. Also, image models often decline to synthesize a recognizable real person's face. The design handles this by composing with the real hype frame and portrait rather than asking the model to redraw the face; see spec 0004 for the fallback if the model still refuses.

## Overview and Minimum Demo Set

| Item | Location | Minimum for MVP | Later |
|---|---|---|---|
| Video clip | `sample_clips/` | 1 gymnastics clip with a clear hype moment | More clips, a second athlete, a control clip with no hype |
| Athlete portrait | `data/assets/athletes/<athlete_id>/portrait.png` | 1 portrait of the athlete | Two or three portraits in different lighting |
| Clip manifest | `sample_clips/manifest.json` | `file`, `sport`, `athlete_id` for the one clip; the agent fills the rest | Hand-tuned `best_frame_s` |
| Athlete profile | `data/athletes.json` | 1 athlete with at least 2 food preferences and 2 interests | More athletes |
| Local businesses | `data/businesses.json` | 3 businesses, each sharing at least 1 tag with the athlete | 6 to 10 businesses, a gymnastics gym as a sports venue |
| Business logos | `data/assets/<business_id>/logo.png` | One logo per business | Storefront and dish photos |
| Ad styles | `data/ad_styles.json` | 2 styles | 3 or 4 styles with reference images |
| Venues | `data/venues.json` | Not required | The LA 2028 gymnastics venue |
| Gemini API key | `.env` | Required | A second key for load spikes during the demo |

## Video Clips

Location: `sample_clips/`. MP4 files are gitignored; the manifest is committed.

Requirements per clip:

- Format MP4 with H.264 video and AAC audio. Resolution 720p or 1080p. Duration between 15 seconds and 3 minutes. Files above roughly 100 MB slow analysis and uploads, so trim to the relevant segment.
- A clearly visible hype moment: the athletic action, the result, and a crowd or commentator reaction, all inside the clip. The video agent uses the reaction to grade hype, so a clip that cuts before the crowd responds will score low.
- Set `athlete_id` in the manifest entry for each clip. That is the simplest path and skips automatic identification. Identification cues in the athlete profile (kit colors, bib number) only matter for clips where you leave `athlete_id` empty.
- At least one frame where the athlete is in a strong pose, well lit, and not motion-blurred. That frame becomes the ad base image.
- For gymnastics specifically: pick a clip that contains the full skill, the landing, and the reaction. A stuck landing or a signature skill with the crowd and commentators reacting is ideal. The best frame is usually mid-air at the peak of the skill or the moment of the stuck landing, and the agent will choose one of those; you can override it in the manifest.
- A control clip with routine play and no reaction is optional for the MVP. It is useful later to confirm the agent does not report a hype moment when there is none.
- Naming: `<sport>_<athlete-id>_<event>.mp4`, for example `gymnastics_simone-biles_floor-final.mp4`.
- Rights: use footage you own, have licensed, or that is clearly permitted for demo use. Broadcast recordings of the actual Olympics are not required for the hackathon and may not be redistributable. Practice footage, self-recorded footage, or openly licensed clips work.

### The clip manifest

`sample_clips/manifest.json` is the record of every clip the system knows about, keyed by file name. It is the one file you edit to control what the pipeline does with a clip. You can start it by hand or let the video agent create entries for you.

Minimal entry you write yourself before the first run. Only `file` is required; `athlete_id` is strongly recommended because it lets the pipeline skip athlete identification entirely:

```json
[
  {
    "file": "gymnastics_simone-biles_floor-final.mp4",
    "sport": "gymnastics",
    "athlete_id": "simone-biles",
    "notes": "Floor routine, final tumbling pass"
  }
]
```

What the video agent adds after analyzing the clip once with Gemini:

```json
{
  "file": "gymnastics_simone-biles_floor-final.mp4",
  "sport": "gymnastics",
  "athlete_id": "simone-biles",
  "analyzed": true,
  "analyzed_by": "gemini",
  "analyzed_at": "2026-09-20T18:04:11Z",
  "notes": "Floor routine, final tumbling pass",
  "moments": [
    {
      "start_s": 58.0,
      "end_s": 66.0,
      "best_frame_s": 61.4,
      "hype_score": 9,
      "description": "Triple-twisting double back, stuck landing, crowd on its feet",
      "event_context": "Women's floor final, last tumbling pass",
      "athlete_hints": { "name": "Simone Biles", "country": "USA", "kit_colors": ["red", "white", "blue"], "bib_number": null, "crowd_reaction": "standing ovation" }
    }
  ]
}
```

How it behaves:

- A clip whose entry is `analyzed: true` is never sent to Gemini again. The pipeline reads the moments from the entry, pulls the frame at `best_frame_s` with ffmpeg, and goes straight to matching and ad generation. This is how you save credits: analyze each clip once, then run the demo as many times as you like.
- You can edit anything in the entry. If you prefer a different, more picturesque moment for the ad, change `best_frame_s` (and the window if you like), set `analyzed_by` to `"manual"`, and the next run uses your timestamp. You can also delete moments you do not want, or add one by hand for a clip that was never analyzed by setting `analyzed: true` and filling in `best_frame_s`.
- If you set `athlete_id`, the matching agent uses that athlete directly. If you leave it null, the matching agent tries to identify the athlete from the hints and writes its answer into the entry for you to check.
- To re-analyze a clip, run `python -m goldcoast detect <clip> --force-analysis`. This replaces the moments but keeps your `athlete_id` and `notes`.
- Renaming a clip file makes it a new clip. Keep names stable.

Recommended workflow for the MVP: pick the one clip, write its minimal entry with `file`, `sport`, and `athlete_id`, run `detect` once, open the manifest, check the timestamp against the video, adjust `best_frame_s` if you prefer a different moment, and commit the manifest. From then on every run is free of video-analysis cost. Add a second clip only after the full flow works for the first.

## Athlete Portrait

Location: `data/assets/athletes/<athlete_id>/portrait.png`, referenced from the athlete profile's `headshot` field as `athletes/<athlete_id>/portrait.png`.

Requirements:

- A clear, front-facing or three-quarter view of the athlete's face and upper body, in focus, evenly lit, at least 1024 px on the long side. PNG or JPEG.
- A plain or uncluttered background so the model reads the subject cleanly.
- Ideally in competition kit or a look consistent with the clip, so the portrait and the hero frame agree.
- Rights: use an image you have permission to use for the demo. Official media kits, press photos with a demo-appropriate license, or a still you extract from your own clip all work.

How it is used: the ad-generation agent sends the portrait alongside the hero frame. When the face is clearly visible in the hero frame, the portrait is a consistency reference only. When it is not, the portrait becomes a foreground cutout overlay next to the business's product, with the hero shot behind. The judge also receives it to check that the athlete in the ad matches. Because the portrait may appear as a cutout, a clean background matters: a plain backdrop or an already-cut-out PNG with transparency gives the best result.

Product visuals: the business's `offerings` list is what the model depicts beside the athlete. If you have a real photo of the signature item, add it under the business's asset folder and list it in `reference_photos`; the ad agent passes the first one to the model.

## Athlete Profiles

Location: `data/athletes.json`, a JSON array of athlete objects.

Required fields:

- `id`: stable slug, for example `jp-archer-01`.
- `name`, `aliases`: full name and any short forms or spellings commentators use.
- `country`, `sport`, `discipline`, `event`.
- `home_city`.

Matching fields, these drive which businesses get ads:

- `favorite_foods`: list of `{ "cuisine": "japanese", "dishes": ["sushi", "katsu curry"] }`. Cuisine values must match tags used in `businesses.json`.
- `interests`: list of tags such as `archery`, `hiking`, `coffee`, `anime`. Interest values must match tags used in `businesses.json`.

Identification fields, these help the video agent confirm who is on screen:

- `identification.kit_colors`: for example `["white", "red"]`.
- `identification.bib_number`: string or null.
- `identification.distinguishing_features`: short phrases such as `"left-handed"`, `"red headband"`.

Portrait field: `headshot`, the path to the athlete portrait under `data/assets/`, for example `athletes/simone-biles/portrait.png`. Required for the MVP athlete because ad generation uses it as a reference; see Athlete Portrait below.

Optional fields: `social_handles`, `fun_facts`.

Guidance:

- The MVP uses a real athlete, Simone Biles. Keep the profile factual and drawn from public interviews and profiles for foods and interests, and treat the generated ads as internal demo material only. Real athletes' names and likenesses in advertising raise publicity-rights issues, and this data feeds directly into ad copy.
- Give the athlete at least two food preferences and two interests so the matching agent has choices. For the MVP, choose interests you can actually match to LA businesses you are willing to add.
- Every cuisine and interest value should appear as a tag on at least one business, otherwise the athlete can never be matched.

## Local Businesses

Location: `data/businesses.json`, a JSON array of business objects. Logos under `data/assets/<business_id>/logo.png`.

Required fields:

- `id`: stable slug, for example `kiro-sushi`.
- `name`, `category`: one of `restaurant`, `cafe`, `bar`, `sports_venue`, `retail`, `experience`.
- `tags`: cuisine and interest tags such as `["japanese", "sushi", "seafood"]` or `["archery", "sports_venue"]`. These are the matching key.
- `address`, `neighborhood`, `nearest_venue`: the Olympic venue this business is close to, matching an id in `venues.json` if that file exists.
- `short_description`: one or two sentences the ad agent can paraphrase.
- `offerings`: signature dishes or services, for example `["omakase", "spicy tuna roll"]`.

Brand fields:

- `logo`: path relative to `data/assets/`, PNG with transparent background, at least 512 px on the long side. Placeholder logos are generated for real businesses until you drop in the actual logo at the same path; the placeholder says PLACEHOLDER on it so it cannot be mistaken for the real thing.
- `brand_colors`: list of hex colors, primary first.
- `tagline`.

Promo fields:

- `offer_text`: the concrete offer to feature, for example `"10% off for ticket holders"`, or `null` when the business is real and has no live promotion. Never invent an offer for a real business; with `null` the ad uses the tagline instead.
- `cta`: for example `"Visit us after the final"`.
- `website`, `instagram`.

Optional fields: `hours`, `price_range`, `reference_photos` (paths under the business's asset folder, for example `prime-pizza-little-tokyo/pepperoni-pizza.jpg`; the first one is shown to the image model as the product visual).

Only the fields above are allowed. Evidence links, copy rules, and research notes go in `data/SOURCES.md`, which the pipeline does not load. Extra keys in the JSON fail validation.

Matching rule: a business is a candidate for an athlete when at least one tag overlaps with the athlete's cuisines or interests. The matching agent then ranks candidates and picks the top ones. A business with no overlapping tag is never matched, so make sure each business carries the exact cuisine or interest tag from the athlete profile (`italian`, `japanese`, `ice_skating`), not only a specific one (`pizza`, `sushi`). Athlete tags that no business uses are allowed and produce a warning from `validate-seed`; an athlete with zero overlapping tags is an error.

## Ad Styles

Location: `data/ad_styles.json`, a JSON array.

Fields:

- `id`, `name`, `description`.
- `mood_keywords`: for example `["electric", "celebratory", "bold"]`.
- `palette`: list of hex colors the style favors.
- `typography_guidance`: a sentence on type weight, case, and placement.
- `layout_notes`: object with `landscape` and `portrait` keys describing where the hero frame, logo, headline, and call to action go for each format.
- `required_elements`: what every ad in this style must contain, for example `["business logo", "offer text", "athlete hero frame"]`. The judge checks these.
- `use_when`: moment or sport types this style suits, for example `["victory", "precision_sport"]`.
- `reference_images`: optional paths under `data/assets/styles/`.

Provide at least two distinct styles for the MVP so the style selection step has a real choice; three or four later.

## Olympic Context (optional)

Location: `data/venues.json`, a JSON array with `id`, `name`, `sport`, `lat`, `lng`, `neighborhood`. Include the venues for each sport in your clips so "nearby" business matching has a reference point.

## Ad Format Specs

Confirm the two target formats and any placement constraints:

- Landscape: 1920 x 1080, 16:9, intended for digital billboards.
- Portrait: 1080 x 1920, 9:16, intended for Instagram Reels and Stories.

If the intended placements have safe zones, maximum text coverage, or logo-size rules, list them here so they can be added to the ad prompt and the judge rubric.

## Credentials

- A Gemini API key from Google AI Studio, placed in `.env` as `GEMINI_API_KEY`. The `google-genai` SDK reads `GEMINI_API_KEY` or `GOOGLE_API_KEY` automatically; if both are set, `GOOGLE_API_KEY` wins. No Google Cloud project is needed.
- Free-tier quotas are limited and video analysis consumes many tokens per clip. Plan on a paid tier or a second key for the demo, and rely on replay mode for rehearsals.
- Never commit `.env`. Copy from `.env.example`.

## Stretch-Goal Data

Only needed if the stretch goal is pursued:

- Sports venues such as archery ranges: add them to `businesses.json` with `category: "sports_venue"` and the sport as a tag.
- Radio ads: preferred voice style, target duration, and any legal disclaimer text.
- Live stream ingestion: HLS or RTMP URLs and stream credentials.

## ID and Naming Conventions

- Ids are lowercase kebab-case, unique within their file, and never reused.
- Tags are lowercase snake_case single tokens, for example `katsu_curry`, `sports_venue`.
- Asset paths are relative to `data/assets/` and use forward slashes.
- Clip names follow `<sport>_<athlete-id>_<event>.mp4` and match the manifest exactly.
