# CoinGecko Highlights Notifier

Project Python nay doc du lieu tu `CoinGecko Highlights`, chi so chung khoan My va chi so chung khoan chau A, sau do gui thong bao qua Telegram va email theo lich:

- 07:00 sang
- 13:00 trua
- 20:00 toi

Mac dinh project dung mui gio `Asia/Bangkok`.

## 1. Tinh nang

- Lay du lieu tu `https://www.coingecko.com/vi/highlights`
- Lay them du lieu chi so chung khoan My:
  - Dow Jones (`^DJI`)
  - Nasdaq (`^IXIC`)
  - S&P 500 (`^GSPC`)
  - Gia vang (`GC=F`)
  - Gia dau WTI (`CL=F`)
  - Gia bac (`SI=F`)
- Lay them du lieu chi so chung khoan chau A:
  - Nikkei 225 (`^N225`)
  - KOSPI (`^KS11`)
  - Shanghai Composite (`000001.SS`)
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
- Ban tin crypto va ban tin chung khoan My duoc gui thanh 2 tin nhan / 2 email rieng
- Ban tin chung khoan My co lich rieng:
  - Mo phien My `09:30 America/New_York`
  - Dong phien My `16:00 America/New_York`
  - Tong hop sang hom sau `07:00 Asia/Bangkok`
- Ban tin chung khoan chau A duoc gom thanh 1 ban tin chung, gui theo gio Viet Nam:
  - Mo phien: `08:30 Asia/Bangkok`
  - Giua phien: `10:00 Asia/Bangkok`
  - Dau phien chieu: `13:00 Asia/Bangkok`
  - Dong cua: `16:30 Asia/Bangkok`
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
    stock_fetcher.py
    stock_formatter.py
  deploy/
    coingecko-notifier.service
    raspberry-pi.md
  scripts/
    bootstrap_pi.sh
    install_systemd_service.sh
    run_now.sh
    run_preview.sh
    run_asia_market_now.sh
    run_asia_market_preview.sh
    run_stock_now.sh
    run_stock_preview.sh
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
- `US_STOCK_ENABLED`
- `US_STOCK_SYMBOLS`
- `US_STOCK_MARKET_TIMEZONE`
- `US_STOCK_MARKET_OPEN_TIME`
- `US_STOCK_MARKET_CLOSE_TIME`
- `US_STOCK_MORNING_TIMEZONE`
- `US_STOCK_MORNING_TIME`
- `US_STOCK_EMAIL_SUBJECT`
- `ASIA_MARKET_ENABLED`
- `ASIA_MARKET_SYMBOLS`
- `ASIA_MARKET_SCHEDULE_SPECS`
- `ASIA_MARKET_EMAIL_SUBJECT`

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

Chi test rieng ban tin chung khoan My:

```bash
python main.py --preview-stock
python main.py --run-stock-once
```

Chi test rieng ban tin chung khoan chau A:

```bash
python main.py --preview-asia-market
python main.py --run-asia-market-once
```

Mac dinh phan chung khoan My su dung cac ma:

- `^DJI` -> Dow Jones
- `^IXIC` -> Nasdaq
- `^GSPC` -> S&P 500

Neu muon doi danh sach, sua trong `.env`:

```text
US_STOCK_SYMBOLS=^DJI,^IXIC,^GSPC,GC=F,CL=F,SI=F,^RUT
```

Mac dinh lich gui cho stock duoc dat theo mui gio thi truong My de tu canh chinh theo DST:

```text
US_STOCK_MARKET_TIMEZONE=America/New_York
US_STOCK_MARKET_OPEN_TIME=09:30
US_STOCK_MARKET_CLOSE_TIME=16:00
US_STOCK_MORNING_TIMEZONE=Asia/Bangkok
US_STOCK_MORNING_TIME=07:00
```

Mac dinh lich gui cho thi truong chau A:

```text
ASIA_MARKET_ENABLED=true
ASIA_MARKET_SYMBOLS=^N225,^KS11,000001.SS
ASIA_MARKET_SCHEDULE_SPECS=08:30@Asia/Bangkok,10:00@Asia/Bangkok,13:00@Asia/Bangkok,16:30@Asia/Bangkok
```

Neu tren Raspberry Pi, ban co the bam script truc tiep:

```bash
./scripts/run_preview.sh
./scripts/run_now.sh
./scripts/run_asia_market_preview.sh
./scripts/run_asia_market_now.sh
./scripts/run_stock_preview.sh
./scripts/run_stock_now.sh
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
