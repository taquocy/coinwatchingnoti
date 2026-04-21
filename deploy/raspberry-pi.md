# Raspberry Pi Deployment

Huong dan nay dung cho Raspberry Pi 4 chay 24/7 voi `systemd`.

## 1. Cai package can thiet

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

## 2. Dua project len Raspberry Pi

Vi du:

```bash
cd /home/pi
git clone <repo-cua-ban> coingecko_notifier
cd coingecko_notifier
```

Hoac copy thu muc project len:

```bash
scp -r coingecko_notifier pi@<ip-pi>:/home/pi/
```

## 3. Bootstrap

```bash
cd /home/pi/coingecko_notifier
chmod +x scripts/*.sh
./scripts/bootstrap_pi.sh
```

Sau do sua file `.env`.

## 4. Test ngay lap tuc

Xem du lieu ma chua gui:

```bash
./scripts/run_preview.sh
```

Gui that ngay lap tuc:

```bash
./scripts/run_now.sh
```

## 5. Cai service tu dong

```bash
./scripts/install_systemd_service.sh
```

Kiem tra:

```bash
sudo systemctl status coingecko-notifier.service
journalctl -u coingecko-notifier.service -f
```

## 6. Dieu khien service

```bash
sudo systemctl start coingecko-notifier.service
sudo systemctl stop coingecko-notifier.service
sudo systemctl restart coingecko-notifier.service
sudo systemctl disable coingecko-notifier.service
```

## 7. Doi mui gio neu can

Mac dinh project dang dung:

```env
TIMEZONE=Asia/Bangkok
```

Neu Raspberry Pi dang dat timezone he thong khac, project van se chay theo timezone trong `.env`.
