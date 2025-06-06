PROJECT_DIR := /root/projects/zozh_bot
VENV_PY := $(PROJECT_DIR)/venv/bin/python3
SERVICE := zozhbot

deploy:
	@echo "📥 Pulling latest code from Git..."
	cd $(PROJECT_DIR) && git pull
	@echo "📦 Installing requirements..."
	cd $(PROJECT_DIR) && $(VENV_PY) -m pip install -r requirements.txt
	@echo "🔁 Restarting bot service..."
	sudo systemctl restart $(SERVICE)
	@echo "✅ Deployment complete. Checking status:"
	sudo systemctl status $(SERVICE)