# Soul - AI Character Image & GIF Generation System

FastAPI-based AI image and video generation system with intelligent deduplication, user-specific variant delivery, and image-to-GIF conversion capabilities.

## 📁 Project Structure

```
soul/
├── app/
│   ├── api/              # API routes
│   │   ├── routes_image.py      # Image generation endpoints
│   │   ├── routes_video.py      # Video/GIF generation endpoints
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
│   │   ├── service_video.py     # Video/GIF generation service
│   │   ├── prompt_cache.py      # Prompt normalization and caching
│   │   ├── place_chooser.py    # Selfie location selection
│   │   └── ai_model_service.py # AI model wrapper
│   ├── model/                   # AI models directory
│   │   ├── sdXL_v10VAEFix.safetensors  # SDXL model
│   │   └── test_svd.py          # SVD testing script
│   ├── config.py                # Configuration management
│   └── test/                    # Test suite
├── static/                      # Frontend files
│   ├── index.html
│   ├── script.js
│   └── style.css
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
- **Web Interface**: http://localhost:8000
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

### Video/GIF Generation

- `GET /video/estimate` - Estimate GIF generation time
  - Query params: `num_frames` (optional)
- `POST /video/generate` - Generate video and GIF from image
  - Body: `{image_path, num_frames?, generate_gif?}`
- `POST /video/generate-from-variant` - Generate GIF from variant ID
  - Query params: `variant_id`, `num_frames?`, `generate_gif?`

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