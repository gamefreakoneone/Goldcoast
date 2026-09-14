# Design

AssetMetadata adds bounded `title` and `description` fields with empty defaults so existing assets remain valid. New `video` uploads require both values and may carry a `product_id`; other asset roles ignore empty labels. AssetEdit uses optional fields so ordinary categorization cannot erase existing video details. The API accepts the two multipart fields and continues to keep uploaded bytes private.

`VideoAnalysis` is the model-produced contract: subject, observations, up to three search queries, uncertainty, `best_frame_s` and `frame_reason`. The worker verifies the timestamp against ffprobe duration, extracts one PNG with the existing media frame extractor, stores it as a tenant-owned `campaign_frame` Resource and returns `VideoEvidence`, which adds the immutable source asset identity, label, description and frame resource identity. The model cannot choose storage identifiers.

The `video_evidence` stage owns analysis and extraction. Its completed output is passed as structured context to planning and both creative directors. The frame is appended to visual references with an explicit source-video label. Campaign results expose optional video evidence, and an authenticated frame-content route serves only frames owned by the requesting tenant. Review renders the evidence without exposing filesystem paths.

Fresh campaigns validate that `video_asset_id` belongs to the tenant and has role `video`. Regeneration copies `video_asset_id` and the completed `video_evidence` output from its source input/checkpoint; the worker restores that output instead of calling Gemini or ffmpeg. Replay retains the source checkpoint and therefore the same frame. Product/testimonial shortcut compatibility remains in backend contracts, but the current web UI offers automatic, product, timely and comic campaigns only.

Telegram video resolution is server controlled. A brief that mentions video selects an exact normalized title contained in the brief. The phrases “latest video”, “last video”, “video I just uploaded” and equivalent possessive wording select the newest tenant video. If several named videos match equally, the command returns a clarifying list and does not call `start_campaign`. A resolved asset ID is included in the internal `WorkflowStart`; public users can already select only their own asset through server validation.

No new database column is needed. Asset and run metadata are JSON resources, and frame bytes use the existing private AssetStore. Existing testimonial endpoints and stored resources remain for backward compatibility while their frontend entry points are removed.

