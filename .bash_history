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
