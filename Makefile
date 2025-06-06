PROJECT_DIR := /root/projects/zozh_bot
VENV_PY := $(PROJECT_DIR)/botvenv/bin/python
VENV_PIP := $(PROJECT_DIR)/botvenv/bin/pip
SERVICE := zozhbot

deploy:
	@echo "📥 Pulling latest code from Git..."
	cd $(PROJECT_DIR) && git pull
	@echo "📦 Installing requirements..."
	cd $(PROJECT_DIR) && $(VENV_PIP) install -r requirements.txt
	@echo "🔁 Restarting bot service..."
	sudo systemctl restart $(SERVICE)
	@echo "✅ Deployment complete. Checking status:"
	sudo systemctl status $(SERVICE)