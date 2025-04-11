apt -y install curl
apt -y install gnupg
curl -s https://deb.frrouting.org/frr/keys.gpg | \
    tee /usr/share/keyrings/frrouting.gpg > /dev/null
apt install lsb-release
FRRVER="frr-stable"
echo deb ’[signed-by=/usr/share/keyrings/frrouting.gpg]’ https://deb.frrouting.org/frr \
    $(lsb_release -s -c) $FRRVER | tee -a /etc/apt/sources.list.d/frr.list
apt update && apt -y install frr frr-pythontools