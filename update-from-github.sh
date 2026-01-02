#!/bin/bash
# update-from-github.sh
# Run: sudo bash update-from-github.sh

set -e  # Exit on error

echo "=== UPDATING PROJECT FROM GITHUB ==="

# 1. Stop services
echo "Stopping services..."
sudo systemctl stop driver-inspection
sudo systemctl stop nginx

# 2. Backup current project
BACKUP_DIR="/home/ubuntu/driver-inspection-backup-$(date +%Y%m%d_%H%M%S)"
echo "Creating backup at: $BACKUP_DIR"
sudo cp -r /home/ubuntu/driver-inspection-app $BACKUP_DIR

# 3. Update from GitHub
echo "Updating from GitHub..."
cd /home/ubuntu/driver-inspection-backup
git pull origin main

# 4. Copy to hosted project (exclude sensitive directories)
echo "Copying files to hosted project..."
sudo rsync -av --delete \
  --exclude='venv' \
  --exclude='uploads' \
  --exclude='ultralytics_cache' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.env' \
  /home/ubuntu/driver-inspection-backup/ \
  /home/ubuntu/driver-inspection-app/

# 5. Fix permissions
echo "Fixing permissions..."
sudo chown -R www-data:www-data /home/ubuntu/driver-inspection-app/uploads
sudo chown -R www-data:www-data /home/ubuntu/driver-inspection-app/ultralytics_cache
sudo chown ubuntu:www-data /home/ubuntu/driver-inspection-app/*.py
sudo chmod 644 /home/ubuntu/driver-inspection-app/*.py
sudo chmod 755 /home/ubuntu/driver-inspection-app/uploads
sudo chmod 755 /home/ubuntu/driver-inspection-app/ultralytics_cache

# 6. Restart services
echo "Restarting services..."
sudo systemctl start driver-inspection
sudo systemctl start nginx

# 7. Wait and check status
sleep 3
echo "Checking service status..."
sudo systemctl status driver-inspection --no-pager | head -20
sudo systemctl status nginx --no-pager | head -10

echo "=== UPDATE COMPLETE ==="
echo "Project updated from GitHub!"
echo "Backup available at: $BACKUP_DIR"