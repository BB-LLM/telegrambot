# Soul - AI Character Image & Video Generation System

FastAPI-based AI image and video generation system with intelligent deduplication, user-specific variant delivery, image-to-GIF conversion, and text-to-video generation capabilities.

## ✨ Features

- **Image Generation**: Generate styled images using Stable Diffusion XL with Soul-specific styles
- **Text-to-Video**: Direct text-to-video generation using Wan API (阿里云 DashScope)
- **Image-to-Video**: Convert images to videos using Stable Video Diffusion (SVD)
- **GIF Conversion**: Automatic MP4 to GIF conversion
- **Intelligent Caching**: Prompt similarity matching and user-specific variant delivery
- **Selfie Generation**: Generate location-based selfies with diverse landmarks

## 📁 Project Structure

```
soul/
├── app/
│   ├── api/              # API routes
│   │   ├── routes_image.py      # Image generation endpoints
│   │   ├── routes_video.py      # Image-to-video generation endpoints (SVD)
│   │   ├── routes_wan_video.py  # Text-to-video generation endpoints (Wan API)
│   │   ├── routes_tasks.py      # Task management endpoints
│   │   ├── routes_style.py      # Style-specific endpoints
│   │   └── routes_static.py     # Static file serving
│   ├── core/
│   │   ├── task_manager.py      # Background task manager with queue
│   │   ├── locks.py             # In-process locking
│   │   ├── ids.py               # ULID generation
│   │   ├── lww.py               # Last Write Wins semantics
│   │   └── idem.py              # Idempotency helpers
│   ├── data/
│   │   ├── models.py            # Pydantic schemas
│   │   └── dal.py               # Data access layer
│   ├── logic/
│   │   ├── service_image.py     # Core image service
│   │   ├── service_video.py     # Image-to-video generation service (SVD)
│   │   ├── service_wan_video.py # Text-to-video generation service (Wan API)
│   │   ├── prompt_cache.py      # Prompt normalization and caching
│   │   ├── place_chooser.py     # Selfie location selection
│   │   └── ai_model_service.py  # AI model wrapper
│   ├── model/                   # AI models directory
│   │   ├── sdXL_v10VAEFix.safetensors  # SDXL model
│   │   └── test_svd.py          # SVD testing script
│   ├── config.py                # Configuration management
│   └── test/                    # Test suite
├── static/                      # Frontend files
│   ├── index.html              # Image generation interface
│   ├── wan_video.html          # Wan video generation interface
│   ├── script.js               # Image generation frontend logic
│   ├── wan_video.js            # Wan video generation frontend logic
│   └── style.css               # Shared styles
├── generated_images/            # Generated image files
├── generated_videos/            # Generated video and GIF files
├── main.py                      # FastAPI application entry
├── init_db.py                   # Database initialization
├── start_server.py              # Server startup script
└── requirements.txt             # Python dependencies
```


## 🛠️ Installation

### 0. python == 3.10, cuda == 12.8

### 1. Clone the Repository

```bash
git clone https://gitlab.com/genimage/soul-mvp.git
cd soul
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3.10 -m venv soul

# Activate (Windows)
soul\Scripts\activate

# Activate (Linux/Mac)
source soul/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: If you need GPU support, install the CUDA-enabled version of PyTorch:
```bash
pip install torch==2.9.0+cu128 torchvision==0.24.0+cu128 --index-url https://download.pytorch.org/whl/cu128
```

### 4. Set Up PostgreSQL Database

**Option A: Using Docker (Recommended)**

```bash
docker run -d \
  --name soul-mvp \
  -e POSTGRES_USER=mvpdbuser \
  -e POSTGRES_PASSWORD=mvpdbpw \
  -e POSTGRES_DB=mvpdb \
  -p 5432:5432 \
  postgres:15.14-alpine3.21
```

**Option B: Local PostgreSQL**

Create a database:
```sql
CREATE DATABASE mvpdb;
CREATE USER mvpdbuser WITH PASSWORD 'mvpdbpw';
GRANT ALL PRIVILEGES ON DATABASE mvpdb TO mvpdbuser;
```

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://mvpdbuser:mvpdbpw@localhost:5432/mvpdb

# Google Cloud Storage (Optional)
GCS_BUCKET_NAME=artifacts-dev-soulmedia
GCS_PROJECT_ID=your-project-id

# GPU Settings (Optional)
FORCE_CPU=false
DEVICE_MEMORY_FRACTION=0.8

# Task Queue Settings
MAX_CONCURRENT_TASKS=1
LOG_LEVEL=INFO

# SVD (Stable Video Diffusion) Settings (Optional)
SVD_MODEL_ID=stabilityai/stable-video-diffusion-img2vid-xt
SVD_OUTPUT_DIR=generated_videos
SVD_NUM_FRAMES=25
SVD_FPS=7
SVD_IMAGE_WIDTH=1024
SVD_IMAGE_HEIGHT=576
SVD_ESTIMATED_SECONDS_PER_FRAME=2.0

# Wan API (Text-to-Video) Settings (Required for text-to-video)
DASHSCOPE_API_KEY=your-dashscope-api-key
WAN_API_BASE_URL=https://dashscope.aliyuncs.com/api/v1
WAN_OUTPUT_DIR=generated_videos
WAN_MODEL=wan2.5-t2v-preview
WAN_SIZE=832*480
WAN_DURATION=5
WAN_PROMPT_EXTEND=true
WAN_WATERMARK=false
```

### 6. Initialize Database

```bash
python init_db.py
```

This will create all necessary tables in the database.

### 7. Download AI Models

Place your AI models in `app/model/` directory:

**Stable Diffusion XL Model (Required for image generation):**
```bash
# Example: Download from Civitai https://civitai.com/models/101055/sd-xl
# Place sdXL_v10VAEFix.safetensors in app/model/
```

**Stable Video Diffusion Model (Optional, for GIF generation):**
The SVD model will be automatically downloaded from Hugging Face when first used:
- Model: `stabilityai/stable-video-diffusion-img2vid-xt`

**Note**: 
- If no SDXL model is provided, the system will run in simulation mode
- SVD model will be downloaded automatically on first use

## 🚀 Running the Server

### Development Mode

```bash
python main.py
```

or

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
python start_server.py
```

Access the application:
- **Image Generation Interface**: http://localhost:8000
- **Wan Video Generation Interface**: http://localhost:8000/wan-video
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/healthz
- **Readiness Check**: http://localhost:8000/ready

## 🧪 Running Tests

```bash
# Run all tests
python -m pytest app/test/

# Run specific test file
python -m pytest app/test/test_database.py -v

# Run with coverage
python -m pytest app/test/ --cov=app
```

## 📝 Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://mvpdbuser:mvpdbpw@localhost:5432/mvpdb` | Database connection string |
| `FORCE_CPU` | `false` | Force CPU-only mode |
| `DEVICE_MEMORY_FRACTION` | `0.8` | GPU memory fraction to use |
| `MAX_CONCURRENT_TASKS` | `1` | Maximum concurrent generation tasks |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SVD_MODEL_ID` | `stabilityai/stable-video-diffusion-img2vid-xt` | SVD model identifier |
| `SVD_NUM_FRAMES` | `25` | Number of frames to generate |
| `SVD_FPS` | `7` | Frame rate for video/GIF |
| `SVD_IMAGE_WIDTH` | `1024` | Input image width |
| `SVD_IMAGE_HEIGHT` | `576` | Input image height |
| `SVD_ESTIMATED_SECONDS_PER_FRAME` | `2.0` | Estimated seconds per frame for time estimation |
| `DASHSCOPE_API_KEY` | - | **Required** for Wan text-to-video. Get from [阿里云百炼](https://help.aliyun.com/zh/model-studio/get-api-key) |
| `WAN_API_BASE_URL` | `https://dashscope.aliyuncs.com/api/v1` | Wan API base URL (Beijing region) |
| `WAN_MODEL` | `wan2.5-t2v-preview` | Wan model identifier |
| `WAN_SIZE` | `832*480` | Video resolution |
| `WAN_DURATION` | `5` | Video duration in seconds |
| `WAN_PROMPT_EXTEND` | `true` | Enable prompt extension |
| `WAN_WATERMARK` | `false` | Enable watermark |

## 📡 API Endpoints

### Image Generation

- `GET /image` - Generate a styled image
  - Query params: `soul_id`, `cue`, `user_id`
- `POST /image/selfie` - Generate a selfie
  - Body: `{soul_id, city_key, mood, user_id}`
- `POST /image/mark-seen` - Mark variant as seen
  - Query params: `variant_id`, `user_id`
- `GET /image/variants/{pk_id}` - Get all variants by prompt key
- `GET /image/user/{user_id}/seen` - Get user's seen variants

### Video/GIF Generation (Image-to-Video, SVD)

- `GET /video/estimate` - Estimate GIF generation time
  - Query params: `num_frames` (optional)
- `POST /video/generate` - Generate video and GIF from image
  - Body: `{image_path, num_frames?, generate_gif?}`
- `POST /video/generate-from-variant` - Generate GIF from variant ID
  - Query params: `variant_id`, `num_frames?`, `generate_gif?`

### Text-to-Video Generation (Wan API)

- `GET /wan-video/` - Generate Soul-style video from text (automatically generates GIF)
  - Query params: `soul_id`, `cue`, `user_id`
  - Returns: `{mp4_url, gif_url, variant_id, pk_id, cache_hit}`
- `POST /wan-video/selfie` - Generate Soul selfie video from text (automatically generates GIF)
  - Body: `{soul_id, city_key, mood, user_id}`
  - Returns: `{mp4_url, gif_url, variant_id, pk_id, landmark_key}`
- `POST /wan-video/generate-direct` - Direct text-to-video generation (for testing)
  - Body: `{positive_prompt, negative_prompt?, seed?, generate_gif?}`

### Task Management

- `GET /tasks/{task_id}` - Get task status
- `DELETE /tasks/{task_id}` - Cancel a task
- `GET /tasks` - List tasks (with filtering)
- `GET /tasks/stats/summary` - Get task statistics

### Style Configuration

- `POST /style` - Create or update style profile
- `GET /style/{soul_id}` - Get style profile
- `DELETE /style/{soul_id}` - Delete style profile
- `GET /style` - List all styles

### Static Files

- `GET /static/image/{filename}` - Get generated image
- `GET /static/videos/{filename}` - Get generated video/GIF
- `GET /static/images` - List all generated images
- `GET /generated/{filename}` - Direct access to generated images

### Health & Info

- `GET /healthz` - Health check
- `GET /ready` - Readiness check
- `GET /info` - Application information
- `GET /docs` - Interactive API documentation (Swagger UI)

## Usage Examples

### Generate an Image

**Via Web Interface:**
1. Select a Soul character
2. Enter a prompt (cue)
3. Click "Generate"
4. Click "Transform to GIF" button to convert to animated GIF

**Via API:**
```bash
# Generate image
curl "http://localhost:8000/image?soul_id=nova&cue=penguin&user_id=user123"

# Convert to GIF (after image generation)
curl -X POST http://localhost:8000/video/generate \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "generated_images/nova_xxx.png",
    "generate_gif": true
  }'
```

### Estimate GIF Generation Time

```bash
curl http://localhost:8000/video/estimate?num_frames=25
```

Response:
```json
{
  "estimated_seconds": 52.0,
  "estimated_minutes": 0.9,
  "video_generation_seconds": 50.0,
  "gif_conversion_seconds": 2.0,
  "num_frames": 25
}
```

### Generate GIF from Variant ID

```bash
curl -X POST "http://localhost:8000/video/generate-from-variant?variant_id=01K8XXX&generate_gif=true"
```

### Generate Video from Text (Wan API)

**Via Web Interface:**
1. Navigate to http://localhost:8000/wan-video
2. Select a Soul character
3. Enter a text prompt (cue)
4. Click "Generate Soul Style Video"
5. The system will automatically generate both MP4 and GIF

**Via API:**
```bash
# Generate style video
curl "http://localhost:8000/wan-video/?soul_id=nova&cue=bird%20flying%20in%20the%20sky&user_id=user123"

# Generate selfie video
curl -X POST http://localhost:8000/wan-video/selfie \
  -H "Content-Type: application/json" \
  -d '{
    "soul_id": "nova",
    "city_key": "tokyo",
    "mood": "happy",
    "user_id": "user123"
  }'
```

Response:
```json
{
  "mp4_url": "/static/videos/wan_01K9XXX.mp4",
  "gif_url": "/static/videos/wan_01K9XXX.gif",
  "variant_id": "01K9XXX",
  "pk_id": "01K8YYY",
  "cache_hit": false
}
```

**Note**: 
- Wan API requires `DASHSCOPE_API_KEY` environment variable
- Videos are automatically downloaded and saved to `generated_videos/` directory
- GIF conversion is automatic (no need to specify)
- The system supports unique variant delivery (same prompt returns different variants for different users)