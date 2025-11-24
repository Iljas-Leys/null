cd ..
git pull
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart machinelearning