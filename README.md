# CoinGecko Highlights Notifier

Project Python nay doc du lieu tu trang `CoinGecko Highlights`, sau do gui thong bao qua Telegram va email theo lich:

- 07:00 sang
- 13:00 trua
- 20:00 toi

Mac dinh project dung mui gio `Asia/Bangkok`.

## 1. Tinh nang

- Lay du lieu tu `https://www.coingecko.com/vi/highlights`
- Tach cac muc noi bat:
  - Tien ao thinh hanh
  - Tang manh nhat
  - Giam manh nhat
  - Tien ao moi
  - Duoc xem nhieu nhat
  - Khoi luong cao nhat
- Gui ban tin den:
  - Telegram Bot
  - Email SMTP
- Chay scheduler hang ngay voi `APScheduler`
- Co che chay thu ngay lap tuc de test
- Co script rieng cho Raspberry Pi 4 chay 24/7 voi `systemd`

## 2. Cau truc thu muc

```text
coingecko_notifier/
  app/
    __init__.py
    config.py
    fetcher.py
    formatter.py
    notifier.py
    scheduler.py
  deploy/
    coingecko-notifier.service
    raspberry-pi.md
  scripts/
    bootstrap_pi.sh
    install_systemd_service.sh
    run_now.sh
    run_preview.sh
    start_scheduler.sh
  .env.example
  main.py
  requirements.txt
  README.md
```

## 3. Cai dat

Neu may chua co Python, hay cai Python 3.11+.

```bash
pip install -r requirements.txt
```

Tao file `.env` tu `.env.example` va dien thong tin:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `EMAIL_*`

## 4. Tao Telegram bot

1. Mo `@BotFather` trong Telegram
2. Dung lenh `/newbot`
3. Lay `TELEGRAM_BOT_TOKEN`
4. Nhan tin nhan bat ky cho bot
5. Lay `chat_id` bang cach goi:

```text
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates
```

## 5. Cau hinh Gmail

Neu dung Gmail:

- Bat `2-Step Verification`
- Tao `App Password`
- Dung `EMAIL_PASSWORD` la App Password, khong dung mat khau dang nhap thong thuong

## 6. Chay project

Chay scheduler:

```bash
python main.py
```

Chay thu ngay 1 lan:

```bash
python main.py --run-once
```

Xem du lieu ngay lap tuc ma chua gui:

```bash
python main.py --preview
```

Neu tren Raspberry Pi, ban co the bam script truc tiep:

```bash
./scripts/run_preview.sh
./scripts/run_now.sh
./scripts/start_scheduler.sh
```

## 7. Trien khai de chay nen

Ban co the chay tren:

- Windows Task Scheduler
- VPS
- Docker
- Railway / Render / EC2

Neu muon de app tu chay 24/7, ban co 2 cach:

- Cach 1: giu app scheduler chay lien tuc bang `python main.py`
- Cach 2: tao 3 task rieng trong Windows Task Scheduler, moi task goi `python main.py --run-once`

Voi Windows, cach 2 thuong on dinh va de quan ly hon.

## 8. Goi y tao Task Scheduler tren Windows

Tao 3 task:

- 07:00 -> chay `python main.py --run-once`
- 13:00 -> chay `python main.py --run-once`
- 20:00 -> chay `python main.py --run-once`

Neu Python cua ban nam o duong dan cu the, vi du:

```text
C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe
```

Thi phan `Program/script` la:

```text
C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe
```

Va phan `Add arguments` la:

```text
main.py --run-once
```

`Start in`:

```text
D:\Projects\Mobile Projects\coingecko_notifier
```

## 9. Luu y

- CoinGecko co the thay doi giao dien HTML bat ky luc nao. Parser trong project duoc viet theo huong linh hoat hon, nhung neu trang doi manh thi can cap nhat.
- Neu Telegram hoac email gui that bai, log se hien loi cu the de debug.
- Neu ban deploy len Raspberry Pi 4, xem them [deploy/raspberry-pi.md](D:\Projects\Mobile%20Projects\coingecko_notifier\deploy\raspberry-pi.md).
