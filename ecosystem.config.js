module.exports = {
  apps: [
    {
      name: "bot-telegram",
      cwd: __dirname,
      script: "main_pro.py",
      interpreter: ".venv/bin/python3",
      autorestart: true,
      max_memory_restart: "300M",
    },
    {
      name: "bot-web",
      cwd: __dirname,
      script: ".venv/bin/gunicorn",
      interpreter: "none",
      args: "-w 1 -b 0.0.0.0:5000 --timeout 30 web_admin:app",
      autorestart: true,
      max_memory_restart: "200M",
    },
    {
      name: "bot-miniapp",
      cwd: __dirname,
      script: ".venv/bin/gunicorn",
      interpreter: "none",
      args: "-w 1 -b 127.0.0.1:5010 --timeout 90 --limit-request-line 4094 mini_app_server:app",
      autorestart: true,
      max_memory_restart: "200M",
    },
    {
      name: "bot-public-tunnel",
      cwd: __dirname,
      script: "scripts/public_tunnel.py",
      interpreter: ".venv/bin/python3",
      autorestart: true,
      restart_delay: 5000,
      max_memory_restart: "150M",
    },
  ],
};
