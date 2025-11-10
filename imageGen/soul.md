0) Goals & Constraints
●Soul-styled image generation: A “soul” (e.g., Nova, Valentina) has a distinctive look and palette controlled by style profiles and LoRA sets fetched from CivitAI.

●Prompt caching with similarity: Similar prompts map to the same PromptKey (normalized + embedding). If a user has already seen all variants under that key, generate a new variant.

●Per-soul catalogs: Catalogs are namespaced by soul. A cue like “penguin” under Nova is distinct from Valentina’s “penguin”.

●User-unique delivery: Never send the same variant twice to the same user.

●Selfies: A soul can “pose” with expression and place (e.g., Nova happy in Paris). If the user requests another selfie in the same place, pick a new landmark or composition in that city.

●MVP stack: FastAPI monolith (+ background worker), Postgres (Cloud SQL), GCS for assets, Cloud Run for deploy. Local dev via Docker Compose.

●Data discipline: LWW semantics; avoid reliance on cross-row transactions, secondary indexes, or materialized views. Query by primary key patterns. Prefer idempotent writes.


1) System Architecture (MVP)
graph TD
  UA[User App]

  subgraph Monolith_Python
    API[FastAPI API]
    Worker[Background worker]
    PromptBuilder[Prompt builder]
    Locking[Best effort in process lock]
  end

  subgraph Style_and_Cache
    StyleProfile[Soul style profiles]
    LoraRegistry[LoRA registry]
    PromptCache[Prompt key store]
    Similarity[Prompt normalization and embeddings]
    PlaceChooser[Landmark diversity chooser]
    Dedupe[Perceptual hash and CLIP filters]
  end

  subgraph Generation_Local
    ModelManager[CivitAI downloader and local cache]
    Animator[Animator or Image generator]
    Transcoder[FFmpeg to GIF]
    ReferenceStore[Soul reference images]
  end

  subgraph State_Tier
    DB[Postgres Cloud SQL]
    ObjectStore[GCS bucket]
  end

  UA --> API
  API --> Worker
  API --> DB
  API --> Locking
  Worker --> PromptBuilder
  Worker --> StyleProfile
  Worker --> LoraRegistry
  Worker --> PromptCache
  Worker --> Similarity
  Worker --> PlaceChooser
  Worker --> ModelManager
  ModelManager --> Animator
  Animator --> Dedupe
  Animator --> Transcoder
  Transcoder --> ObjectStore
  ObjectStore --> API
  ReferenceStore --> Animator
  DB --- API
  DB --- Worker
Deployment
●Local: Docker Compose (api + worker in same image, optional GPU container for generation).

●Cloud: Cloud Run service for API and worker; Cloud SQL Postgres; GCS bucket for assets; Cloud Logging.


2) Core Sequence (Cue drawing, soul-style, cached, user-unique)
sequenceDiagram
    autonumber
    participant UA as User App
    participant Soul as Soul Nova
    participant API as FastAPI
    participant DB as Postgres
    participant Cache as Prompt Cache
    participant Hist as Seen History
    participant Style as Style Profile
    participant DL as CivitAI Manager
    participant Gen as Generator or Animator
    participant TR as Transcoder
    participant GCS as GCS

    UA->>Soul: request penguin for user U1
    Soul->>API: create job soul Nova cue penguin user U1
    API->>Cache: find similar key for Nova penguin
    alt cache hit
        Cache-->>API: key K and variant list
        API->>Hist: lookup unseen variant for U1 in K
        alt unseen exists
            Hist-->>API: variant vX
            API->>Hist: record seen U1 vX
            API-->>UA: deliver vX url
        else all seen
            API->>Style: resolve style and loras for Nova
            API->>DL: ensure models and loras
            DL-->>API: ready
            API->>Gen: render new variant with new seed
            Gen-->>API: frames or png
            API->>TR: to gif
            TR-->>API: gif file
            API->>GCS: store object
            GCS-->>API: url and asset id
            API->>Cache: append variant under K
            API->>Hist: record seen U1 asset
            API-->>UA: deliver url
        end
    else cache miss
        API->>Style: resolve style and loras for Nova
        API->>DL: ensure models and loras
        DL-->>API: ready
        API->>Gen: render first variant
        Gen-->>API: frames or png
        API->>TR: to gif
        TR-->>API: gif file
        API->>GCS: store object
        GCS-->>API: url and asset id
        API->>Cache: create key K and add variant
        API->>Hist: record seen U1 asset
        API-->>UA: deliver url
    end

3) Data Model (Postgres) — LWW, denormalized, key-based
Principles
●Every table has pk that answers our primary query path. No cross-table joins required in the hot path.

●LWW fields: updated_at_ts BIGINT (epoch ms). On write, set updated_at_ts = now_ms(). Readers accept the row with the greatest updated_at_ts, tie-break on pk.

●Idempotency: All write APIs accept an optional idempotency_key to avoid duplicates on retries.

●No reliance on secondary indexes in design. In Postgres we may add them for speed, but queries must work by PK.

Note: Type names and constraints are chosen for MVP speed. Keep it simple.
3.1 Souls and styles
-- Soul namespace; few rows
CREATE TABLE soul (
  soul_id          TEXT PRIMARY KEY,            -- e.g., "nova", "valentina"
  display_name     TEXT NOT NULL,
  updated_at_ts    BIGINT NOT NULL
);

-- Style profile is denormalized and versioned; only fetch by soul_id
CREATE TABLE soul_style_profile (
  soul_id          TEXT PRIMARY KEY,
  base_model_ref   TEXT NOT NULL,               -- civitai identifier or local tag
  lora_ids_json    JSONB NOT NULL,              -- ["loraA@v1", "loraB@v2"]
  palette_json     JSONB NOT NULL,              -- colors, stroke hints
  negatives_json   JSONB NOT NULL,              -- negative prompts
  motion_module    TEXT,                        -- optional animation module
  extra_json       JSONB NOT NULL DEFAULT '{}', -- freeform knobs
  updated_at_ts    BIGINT NOT NULL
);
3.2 Prompt keys and variants (catalog per soul)
-- PromptKey is the cache key for "similar prompts" under a soul
CREATE TABLE prompt_key (
  pk_id            TEXT PRIMARY KEY,            -- soul_id + ":" + key_hash
  soul_id          TEXT NOT NULL,
  key_norm         TEXT NOT NULL,               -- normalized text
  key_hash         TEXT NOT NULL,               -- e.g., sha1 of norm
  key_embed        BYTEA,                       -- optional; brute-force scan in app
  meta_json        JSONB NOT NULL DEFAULT '{}', -- e.g., canonical prompt
  updated_at_ts    BIGINT NOT NULL
);

-- Variants are stored per PromptKey; hot path reads by pk_id
CREATE TABLE variant (
  variant_id       TEXT PRIMARY KEY,            -- ulid
  pk_id            TEXT NOT NULL,               -- prompt_key.pk_id
  soul_id          TEXT NOT NULL,               -- duplicate for easy filtering
  asset_url        TEXT NOT NULL,               -- GCS signed or path
  storage_key      TEXT NOT NULL,               -- gs://bucket/path
  seed             BIGINT,
  phash            BIGINT,                      -- perceptual hash for dedupe
  meta_json        JSONB NOT NULL DEFAULT '{}', -- frame count, sampler, etc
  updated_at_ts    BIGINT NOT NULL
);

-- Minimal mapping to fetch variants by key without a join (dup soul_id)
-- Access pattern: GET all variants by pk_id; app filters unseen in memory.
3.3 User seen history (user-unique delivery)
-- Keyed for direct membership check without join-heavy logic
CREATE TABLE user_seen (
  user_id          TEXT NOT NULL,
  variant_id       TEXT NOT NULL,
  seen_at_ts       BIGINT NOT NULL,
  PRIMARY KEY (user_id, variant_id)
);
3.4 Landmarks for selfie diversity
CREATE TABLE landmark_log (
  soul_id          TEXT NOT NULL,
  city_key         TEXT NOT NULL,               -- e.g., "paris"
  landmark_key     TEXT NOT NULL,               -- e.g., "louvre", "montmartre"
  user_id          TEXT,                        -- null means global use
  used_at_ts       BIGINT NOT NULL,
  PRIMARY KEY (soul_id, city_key, landmark_key, COALESCE(user_id, ''))
);
3.5 Locks and idempotency (best effort)
-- Best-effort logical lock with TTL semantics, LWW overwrite allowed
CREATE TABLE work_lock (
  lock_key         TEXT PRIMARY KEY,            -- e.g., "nova|penguin"
  owner_id         TEXT NOT NULL,               -- ulid or hostname
  expires_at_ts    BIGINT NOT NULL,
  updated_at_ts    BIGINT NOT NULL
);

-- Optional: record idempotency to dedupe retries
CREATE TABLE idempotency (
  idem_key         TEXT PRIMARY KEY,
  result_json      JSONB NOT NULL,
  updated_at_ts    BIGINT NOT NULL
);
Why this shape:
●All lookups by PK (prompt_key.pk_id, variant.variant_id, user_seen(user,variant), work_lock.lock_key).

●No multi-row transactions are required; every write is single-row LWW.

●Denormalization (duplicate soul_id) keeps read paths simple.


4) GCS Object Layout
●Bucket: artifacts-<env>-soulmedia

●Paths:

○soul/<soul_id>/key/<key_hash>/variant/<variant_id>.gif

○Optional sidecars: .../<variant_id>.json (metadata), .../<variant_id>.png (cover)

Use V4 signed URLs for delivery. Keep bucket private.

5) Prompt Normalization and Similarity
Normalization (deterministic):
●lowercase, strip punctuation, squash whitespace

●remove stopwords, sort key tokens

●add fixed style tags from the soul (e.g., “anime pastel outlines”)

Embedding:
●Use a small local text embedder (e.g., sentence-transformers miniature) in the app.

●Store embedding bytes in prompt_key.key_embed.

●MVP similarity: brute-force cosine in Python on the candidate set for that soul. We will keep it small; no extra infra.

Cache policy:
●If cosine_sim >= 0.85, reuse the same pk_id. Otherwise, create a new pk_id.


6) Place Chooser (Selfie diversity)
Seed a small JSON list per city with landmark keys (e.g., paris: ["eiffel", "louvre", "montmartre", "pont_alexandre_iii"]).
Algorithm:
1.Get landmark_log rows for (soul_id, city_key) with optional user_id.

2.Pick an unused landmark; if all used, pick the least recently used.

3.Write landmark_log row (LWW, no transaction).

4.Add the landmark token to the prompt (and a different camera angle if reused).


7) Generation Pipeline
Two modes, both driven by LoRAs from CivitAI:
●Static to subtle GIF: text2img to PNG, then 6–12 img2img variations (low strength), stitch with FFmpeg.

●Animated: AnimateDiff or Stable Video Diffusion to frames or short MP4, then FFmpeg to GIF.

ModelManager
●Inputs: list of base_model_ref, lora_ids_json, optional motion_module.

●Strategy:

○On first use, download from CivitAI to a writable local volume.

○For Cloud Run: download to /tmp on cold start; optionally keep a warm cache in a dedicated GCS folder and copy down on boot (checksum-based).

Transcoder
●ffmpeg -i input.mp4 -vf "fps=12,scale=512:-1:flags=lanczos" -loop 0 output.gif

●For image sequences: ffmpeg -r 12 -i frame_%03d.png -vf "scale=512:-1:flags=lanczos" -loop 0 out.gif.

Dedupe
●Compute phash on the final GIF; if distance < threshold to an existing variant in the same key, discard and regenerate.


8) API Surface (MVP)
Routes
●GET /image?soul_id&cue&user_id

 Returns {url, variant_id, pk_id}. Always user-unique: unseen variant or fresh one.

●POST /selfie body: {soul_id, city_key, mood, user_id}

 Returns {url, variant_id, pk_id, landmark_key}.

●POST /style body: {soul_id, base_model_ref, lora_ids, palette, negatives, motion_module}

 Upserts soul_style_profile (LWW).

●POST /ingest/reference body: {soul_id, url}

 Adds reference image record for the soul; stored in ReferenceStore (can be a folder in GCS, indexed in a small table if needed).

●POST /admin/rebuild_prompt_key rare use; recompute normalization and embedding.

Headers
●Idempotency-Key optional; if provided, read/write idempotency table.


9) Worker Logic (Pseudocode)
def get_or_create_variant(soul_id, cue, user_id):
    key_norm = normalize(cue, soul_id)
    pk = cache_find_or_create_pk(soul_id, key_norm)  # returns pk_id

    variants = db_list_variants(pk)                  # by pk_id
    unseen = filter_unseen(user_id, variants)        # in memory set diff

    if unseen:
        v = pick_best(unseen)                        # e.g., newest first
        mark_seen(user_id, v.variant_id)
        return v

    # need new variant
    style = db_get_style(soul_id)
    models_ready = model_manager_ensure(style)
    prompt = prompt_builder(style, cue)

    artifact = generator_render(style, prompt)       # png, frames, or mp4
    gif = transcode_to_gif(artifact)
    dedupe_guard(pk, gif)                            # phash threshold

    asset_id = ulid()
    storage_key = gcs_put(soul_id, pk, asset_id, gif)
    asset_url = signed_url(storage_key)

    v = variant_row(asset_id, pk, soul_id, asset_url, seed=random_seed())
    db_put_variant(v)                                # single-row LWW
    mark_seen(user_id, v.variant_id)

    return v
Locking
For MVP, since the monolith can run single instance or a small pool, use an in-process asyncio lock keyed by soul_id + ":" + key_norm to reduce duplicate work. If duplicates happen, LWW writes are safe; dedupe via phash.

10) SQL DDL (copy-paste ready)
-- souls
CREATE TABLE IF NOT EXISTS soul (
  soul_id       TEXT PRIMARY KEY,
  display_name  TEXT NOT NULL,
  updated_at_ts BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS soul_style_profile (
  soul_id          TEXT PRIMARY KEY,
  base_model_ref   TEXT NOT NULL,
  lora_ids_json    JSONB NOT NULL,
  palette_json     JSONB NOT NULL,
  negatives_json   JSONB NOT NULL,
  motion_module    TEXT,
  extra_json       JSONB NOT NULL DEFAULT '{}',
  updated_at_ts    BIGINT NOT NULL
);

-- prompt key
CREATE TABLE IF NOT EXISTS prompt_key (
  pk_id         TEXT PRIMARY KEY,
  soul_id       TEXT NOT NULL,
  key_norm      TEXT NOT NULL,
  key_hash      TEXT NOT NULL,
  key_embed     BYTEA,
  meta_json     JSONB NOT NULL DEFAULT '{}',
  updated_at_ts BIGINT NOT NULL
);

-- variant
CREATE TABLE IF NOT EXISTS variant (
  variant_id    TEXT PRIMARY KEY,
  pk_id         TEXT NOT NULL,
  soul_id       TEXT NOT NULL,
  asset_url     TEXT NOT NULL,
  storage_key   TEXT NOT NULL,
  seed          BIGINT,
  phash         BIGINT,
  meta_json     JSONB NOT NULL DEFAULT '{}',
  updated_at_ts BIGINT NOT NULL
);

-- seen
CREATE TABLE IF NOT EXISTS user_seen (
  user_id       TEXT NOT NULL,
  variant_id    TEXT NOT NULL,
  seen_at_ts    BIGINT NOT NULL,
  PRIMARY KEY (user_id, variant_id)
);

-- landmark diversity
CREATE TABLE IF NOT EXISTS landmark_log (
  soul_id       TEXT NOT NULL,
  city_key      TEXT NOT NULL,
  landmark_key  TEXT NOT NULL,
  user_id       TEXT,
  used_at_ts    BIGINT NOT NULL,
  PRIMARY KEY (soul_id, city_key, landmark_key, COALESCE(user_id, ''))
);

-- best-effort lock
CREATE TABLE IF NOT EXISTS work_lock (
  lock_key      TEXT PRIMARY KEY,
  owner_id      TEXT NOT NULL,
  expires_at_ts BIGINT NOT NULL,
  updated_at_ts BIGINT NOT NULL
);

-- idempotency
CREATE TABLE IF NOT EXISTS idempotency (
  idem_key      TEXT PRIMARY KEY,
  result_json   JSONB NOT NULL,
  updated_at_ts BIGINT NOT NULL
);
Add indexes only for convenience, not as a dependency (e.g., CREATE INDEX ON prompt_key(soul_id)). Keep code paths working by PK reads.

11) Code Organization
/app
  /api
    routes_image.py
    routes_selfie.py
    routes_style.py
    deps.py
  /core
    lww.py                 # now_ms, lww_upsert helpers
    ids.py                 # ULID generator
    locks.py               # in-process keyed locks
    idem.py                # idempotency helpers
  /data
    models.py              # pydantic schemas
    dal.py                 # PK-based CRUD for each table
  /gen
    civitai.py             # download and cache models/loras
    builder.py             # prompt builder
    animator.py            # AnimateDiff or fallback
    transcode.py           # ffmpeg helpers
    dedupe.py              # phash and CLIP filters
  /logic
    prompt_cache.py        # normalize, embed, cache key
    place_chooser.py
    service_image.py       # get_or_create_variant
  main.py                  # FastAPI app, routes
  worker.py                # background tasks

12) Tasks for the Engineer
1.Postgres schema: Apply DDL above to Cloud SQL. Create a dev DB locally via Docker Compose.

2.GCS bucket: Create artifacts-<env>-soulmedia; service account with object admin; implement signed URL helper.

3.CivitAI integration:

○Minimal downloader that takes base_model_ref, lora_ids_json, motion_module and mirrors them into a local folder.

○On Cloud Run boot, optionally sync from a models cache folder in GCS to /tmp/models.

4.Prompt cache and similarity:

○Implement normalize(cue, soul_id) and an embedder (tiny model).

○Brute-force cosine over candidate keys for the soul; threshold 0.85.

5.Variant flow:

○Implement get_or_create_variant as above.

○Implement dedupe by phash within the same pk_id.

6.Selfie flow:

○Build place_chooser with a hardcoded JSON list for Paris and two other cities.

○Log usage to landmark_log.

7.API endpoints (see §8).

8.Worker:

○Use FastAPI BackgroundTasks for MVP.

○If you split to a process: simple queue via HTTP call back into the same service (keep it simple).

9.Observability:

○Log: cache_hit, cache_miss, generation_ms, gif_size_bytes, gcs_put_ms.

○Add a very simple /healthz.

10.Security:

●All delivered URLs are signed and short-lived.


13) Acceptance Criteria
●Requesting GET /image?soul_id=nova&cue=penguin&user_id=u1 twice yields two different variants for the same user.

●Requesting the same for user_id=u2 returns the first variant (cache hit) if available.

●Requesting POST /selfie with {soul_id:nova, city_key:paris, mood:happy, user_id:u1} twice yields different landmarks or angles.

●Variants appear at gs://artifacts-<env>-soulmedia/soul/nova/key/<hash>/variant/<ulid>.gif.

●No errors when running locally in Docker Compose and deploying to Cloud Run.


Closing
Build it LWW, key-based, and denormalized so we rely on simple primary-key lookups and single-row writes. In Postgres today, that keeps the code straightforward; later, this shape lets us move to a wide-column, eventually-consistent store without redesigning flows. For now, keep your mental model: no cross-row transactions needed, no dependence on secondary indexes, and every hot path is a PK read.

