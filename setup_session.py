import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

import config


def setup_session():
    """
    Görünür (headed) bir Chrome penceresi açar, kullanıcının Quiz.com'a giriş
    yapmasını bekler ve oturum çerezlerini session.json dosyasına depolar.
    """
    print("\n" + "=" * 65)
    print("      🔐 QUIZ.COM OTURUM KAYDETME ARACI (SETUP SESSION)      ")
    print("=" * 65)
    print("\n>>> Tarayıcı açılıyor, lütfen bekleyin...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        
        print(">>> Quiz.com giriş sayfası açılıyor...")
        page.goto(config.QUIZ_COM_LOGIN_URL, wait_until="domcontentloaded")
        
        print("\n" + "=" * 65)
        print("📌 ŞU AN TARAYICI PENCERESİ AÇILDI!")
        print("1. Açılan pencerede Quiz.com hesabınıza giriş yapın.")
        print("2. Giriş tamamlanınca bu terminale dönüp aşağıdaki tuşa basın.")
        print("=" * 65 + "\n")
        
        input(">>> Giriş yaptıktan sonra oturumu kaydetmek için ENTER'A BASIN: ")
        
        # Oturum durumunu kaydet
        context.storage_state(path=str(config.SESSION_FILE))
        print(f"\n✅ [BAŞARILI] Oturum durumu '{config.SESSION_FILE}' dosyasına kaydedildi!")
        print("Artık quiz-maker-agent arka planda sizin adınıza yarışmaları hazırlayabilir.\n")
        browser.close()


def ensure_quizcom_session():
    """
    Oturum dosyası var mı kontrol eder, yoksa kullanıcıyı yönlendirerek kurulumu başlatır.
    """
    if not config.SESSION_FILE.exists():
        print("\n[BİLGİ] Quiz.com oturum dosyası (session.json) bulunamadı.")
        print("Quiz oluşturabilmek için bir kez oturum açmanız gerekiyor.")
        setup_session()


if __name__ == "__main__":
    setup_session()
