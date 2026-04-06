# UcuzUçuş Telegram Bot 🛫

Her 6 saatte bir ucuz uçuşları tarayıp Telegram grubuna gönderir.

## Kurulum
Bu repo GitHub Actions ile otomatik çalışır. Herhangi bir şey yapmana gerek yok.

## Ayarlar
`bot.yml` dosyasında değiştirebilirsin:
- `MAX_PRICE` — Maksimum fiyat (TL)
- `cron` — Ne sıklıkla çalışsın (`0 */6 * * *` = her 6 saat)
- `ROUTES` — Hangi rotalar taransın
