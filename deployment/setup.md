Be on local network / vpn

cd ~
mkdir machinelearning
cd machinelearning
git clone https://github.com/Iljas-Leys/null

ssh user@192.168.0.200@user
sudo nano /etc/systemd/system/machinelearning.service

[Unit]
Description=machineLearning
After=network.target
[Service]
WorkingDirectory=/home/user/machinelearning/null
ExecStart=/home/user/machinelearning/null/.venv/bin/streamlit run /home/user/machinelearning/null/app.py --server.address=0.0.0.0 --server.port=8501
Restart=always
User=user
Group=user
[Install]
WantedBy=multi-user.target

sudo systemctl enable machinelearning
sudo systemctl start machinelearning