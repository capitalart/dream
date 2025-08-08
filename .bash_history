sudo whoami
cd ~
pwd
git init
git remote add origin git@github.com:capitalart/dream.git
git branch -m main 
git push -u origin main   
su - dream
cd ~
touch testfile.txt
nano ~/.ssh/config
exit
cat ~/.ssh/dream.pub
exit
mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chown -R dream:dream ~/.ssh
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chown -R dream:dream ~/.ssh
nano ~/.ssh/config
exit
./project-toolkit.sh
pip install pytest-check-links
pip freeze > requirements.txt
./project-toolkit.sh
nano pytest.ini
./project-toolkit.sh
rm tools/test_validate_sku_integrity.py
./project-toolkit.sh
git apply codex-patch-01.html
git reset --hard
git add .
git checkout main
./project-toolkit.sh
sudo systemctl stop dreamartmachine && sudo systemctl start dreamartmachine && journalctl -u dreamartmachine -f
source ~/venv/bin/activate
./project-toolkit.sh
sudo systemctl stop dreamartmachine && sudo systemctl start dreamartmachine && journalctl -u dreamartmachine -f
source ~/venv/bin/activate
nano ~/.bashrc
