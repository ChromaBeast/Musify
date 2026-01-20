# Musify 🎵

Convert Spotify playlists to downloadable MP3 ZIP files.

## Quick Start

### Local Development
```bash
# Backend
docker-compose up --build

# Frontend  
cd frontend && npm install && npm run dev
```

---

## VPS Deployment Guide (Oracle Cloud)

### Step 1: Prepare Your VPS

SSH into your Oracle VPS and run:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in for docker group to take effect
exit
```

### Step 2: Clone the Repo

```bash
ssh your-vps
cd ~
git clone https://github.com/YOUR_USERNAME/Musify.git musify
cd musify
```

### Step 3: Configure Spotify Credentials

```bash
# Create .env file
cat > .env << EOF
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
EOF
```

### Step 4: Open Firewall Ports

For Oracle Cloud, open ports in the **VCN Security List**:
1. Go to Oracle Cloud Console → Networking → Virtual Cloud Networks
2. Click your VCN → Security Lists → Default Security List
3. Add Ingress Rule:
   - Source: `0.0.0.0/0`
   - Destination Port: `8000`
   - Protocol: TCP

Also open on the VPS itself:
```bash
sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

### Step 5: Start the Backend

```bash
cd ~/musify
docker-compose up -d --build
```

Test it: `curl http://YOUR_VPS_IP:8000`

---

## Auto-Deploy Setup (GitHub Actions)

### Add GitHub Secrets

Go to your GitHub repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret Name | Value |
|-------------|-------|
| `VPS_HOST` | Your VPS public IP (e.g., `129.146.xx.xx`) |
| `VPS_USERNAME` | SSH username (e.g., `ubuntu`) |
| `VPS_SSH_KEY` | Your private SSH key (paste entire key) |
| `SPOTIFY_CLIENT_ID` | From Spotify Developer Dashboard |
| `SPOTIFY_CLIENT_SECRET` | From Spotify Developer Dashboard |

### Generate SSH Key (if needed)

```bash
# On your local machine
ssh-keygen -t ed25519 -f ~/.ssh/musify_deploy

# Copy public key to VPS
ssh-copy-id -i ~/.ssh/musify_deploy.pub ubuntu@YOUR_VPS_IP

# The PRIVATE key (~/.ssh/musify_deploy) goes in GitHub Secrets
```

### Test Deployment

Push to `main` branch → GitHub Actions will auto-deploy!

---

## Frontend Deployment (Vercel)

1. Import repo on [vercel.com](https://vercel.com)
2. Set root directory to `frontend`
3. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = `http://YOUR_VPS_IP:8000`
4. Deploy!

---

## Features

- ✅ Auto-cleanup after 30 minutes
- ✅ Real-time progress updates
- ✅ Beautiful dark UI
- ✅ Docker deployment
- ✅ GitHub Actions CI/CD
