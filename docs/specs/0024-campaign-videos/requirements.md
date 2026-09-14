# 0024 Campaign videos

Replace the testimonial-facing workflow with reusable, owner-labeled campaign videos. A manager uploads an MP4, gives it a clear name and description, optionally associates it with a confirmed product, and can select it on Today or refer to the most recently uploaded video from Telegram. Existing testimonial records and campaigns remain readable for compatibility, but testimonial upload, analysis, allowance and campaign controls are removed from the current web experience.

For a live campaign with a video, the video agent must describe only visible evidence, select one best-frame timestamp inside the clip, explain that choice and propose bounded discovery searches. Goldcoast extracts the selected frame into tenant-owned storage. Discovery combines those queries with current local, cultural and eligible weather evidence. Planning and both creative producers receive the typed video evidence; the selected frame is supplied as a labeled visual reference. Video labels and descriptions are owner context, not authority to invent products, prices, offers or third-party facts.

Campaign Review must show the source video name, description, selected frame, timestamp, frame rationale and observations. Regeneration reuses the original video evidence and frame without another video-analysis call or a different frame. Replay also reuses recorded evidence and makes zero provider calls. Historical video campaigns without the new fields remain readable.

Telegram `/campaign` requests that refer to a video resolve an exact title when possible and otherwise resolve phrases such as “the video I just uploaded” to the tenant’s latest campaign video. The confirmation names the selected video. Missing or ambiguous video references are rejected before a campaign grant is reserved.

MP4 uploads remain limited to ten megabytes and sixty seconds. New campaign videos require a name and description. The business profile remains the source of truth for product identity and offers, including limited-time offers.

