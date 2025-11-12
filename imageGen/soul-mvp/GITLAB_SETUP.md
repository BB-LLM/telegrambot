# GitLab Setup Guide

## 📤 How to Upload to GitLab

### Step 1: Initialize Git Repository

```bash
cd soul
git init
```

### Step 2: Create .gitignore (if not exists)

The `.gitignore` file should already exist with these rules:
- Python cache files (`__pycache__/`, `*.pyc`)
- Virtual environment (`venv/`, `env/`)
- Generated images (`generated_images/`)
- Model files (`.safetensors`, `.ckpt`)
- Environment files (`.env`)
- IDE files (`.vscode/`, `.idea/`)

### Step 3: Add and Commit Files

```bash
git add .
git commit -m "Initial commit: Soul MVP AI image generation system"
```

### Step 4: Connect to GitLab

```bash
# Add remote repository
git remote add origin https://gitlab.com/your-username/soul-mvp.git

# Or using SSH
git remote add origin git@gitlab.com:your-username/soul-mvp.git
```

### Step 5: Push to GitLab

```bash
git branch -M main
git push -u origin main
```

## ✅ Verification Checklist

After upload, verify on GitLab:
- ✓ All code files are present
- ✓ `generated_images/` directory NOT uploaded (check .gitignore)
- ✓ `.env` file NOT uploaded (check .gitignore)
- ✓ Large model files NOT uploaded (check .gitignore)
- ✓ README.md is visible
- ✓ requirements.txt is present

## 🔄 Updating Existing Repository

```bash
# Make changes to files

# Add changes
git add .

# Commit changes
git commit -m "Update: describe your changes"

# Push to GitLab
git push origin main
```

## 🚀 Next Steps After Upload

1. **Set up CI/CD** (optional): Create `.gitlab-ci.yml` for automated testing
2. **Add collaborators**: Invite team members to the project
3. **Configure secrets**: Add environment variables in GitLab CI/CD settings
4. **Create issues**: Document bugs, features, or improvements

## 📋 Branch Strategy (Recommended)

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "Add new feature"

# Push to GitLab
git push origin feature/new-feature

# Create merge request on GitLab web interface
```
