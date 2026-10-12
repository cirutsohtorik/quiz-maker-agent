import os
import sys

# Windows terminal UTF-8 encoding fix
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import argparse
from typing import Optional

import config
from setup_session import ensure_quizcom_session
from modules.question_generator import generate_quiz_questions, DIFFICULTY_PRESETS
from modules.quizcom_automator import QuizComAutomator


def print_banner():
    print("=" * 65)
    print("           🎮 QUIZ-MAKER-AGENT: AKILLI YARIŞMA AJANI           ")
    print("=" * 65)
    print("📌 SİSTEM GEREKSİNİMLERİ & KISITLAMALAR:")
    print(" • LLM Motoru : Yalnızca Google Gemini API (ücretsiz API anahtarı: aistudio.google.com)")
    print(" • Tarayıcı   : Playwright Chromium (Varsayılan: Arka planda çalışır)")
    print(" • Platform   : Quiz.com hesabı gereklidir (1 kez giriş yeterlidir)")
    print(" • Çıktı      : 20 soru, 4 şıklı buton modu ve otomatik GIPHY eşleşmesi")
    print("=" * 65)


def ensure_gemini_api_key() -> str:
    """
    Gemini API anahtarı yoksa kullanıcıdan interaktif olarak ister ve .env'ye kaydeder.
    """
    api_key = config.GEMINI_API_KEY.strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        print("\n🔑 [GEREKLİ] Google Gemini API anahtarınız henüz ayarlanmamış!")
        print("💡 Ücretsiz API anahtarınızı hemen buradan alabilirsiniz: https://aistudio.google.com/")
        entered_key = input("👉 Lütfen Gemini API Anahtarınızı yapıştırın: ").strip()
        
        if not entered_key:
            print("\n[Hata] API anahtarı girilmedi. İşlem durduruldu.")
            sys.exit(1)
            
        env_path = config.BASE_DIR / ".env"
        # .env dosyasına ekle veya güncelle
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\nGEMINI_API_KEY={entered_key}\n")
            
        config.GEMINI_API_KEY = entered_key
        print("✅ API anahtarınız .env dosyasına güvenle kaydedildi!\n")
        return entered_key
    return api_key


def ask_difficulty_level(default: int = 4) -> int:
    """
    Kullanıcıya 7 farklı zorluk kombinasyonunu sunar ve seçimini alır.
    Boş bırakılırsa (ENTER) varsayılan olarak 4 (Kolay - Orta) seçilir.
    """
    print("\n" + "-" * 65)
    print("🎯 ZORLUK SEVİYESİ SEÇİN:")
    for key, val in DIFFICULTY_PRESETS.items():
        suffix = " [Varsayılan]" if key == default else ""
        print(f" [{key}] {val['name']:<20} ({val['description']}){suffix}")
    print("-" * 65)

    while True:
        choice_str = input(f"👉 Seçiminiz (1-7) [Varsayılan: {default}]: ").strip()
        if not choice_str:
            return default
        if choice_str.isdigit() and int(choice_str) in DIFFICULTY_PRESETS:
            return int(choice_str)
        print("⚠️ Lütfen 1 ile 7 arasında geçerli bir numara girin.")


def run_quiz_agent(
    topic: Optional[str] = None,
    difficulty: Optional[int] = None,
    auto_host: bool = False,
    headless: bool = True
):
    print_banner()

    # 1. API Anahtarı Doğrulaması
    ensure_gemini_api_key()

    # 2. Quiz.com Oturum Doğrulaması (Yoksa otomatik tarayıcı açıp kaydettirir)
    ensure_quizcom_session()
    
    # 3. Konu ve Zorluk Seviyesi Alımı
    if not topic:
        print("\nAgent hazır! Bana dilediğiniz herhangi bir konu veya konuları söyleyin.")
        topic = input("👉 Quiz Konusu: ").strip()
        
    if not topic:
        print("[Hata] Bir konu belirtilmedi. Çıkılıyor.")
        return

    if difficulty is None or difficulty not in DIFFICULTY_PRESETS:
        difficulty = ask_difficulty_level(default=4)

    preset = DIFFICULTY_PRESETS[difficulty]
    print(f"\n[1/3] Konu alındı: '{topic}'", flush=True)
    print(f"🎯 Seçilen Zorluk: {preset['name']} ({preset['description']})", flush=True)
    print("Gemini API ile sorular üretiliyor ve harmanlanıyor...", flush=True)
    
    try:
        quiz_data = generate_quiz_questions(
            topic=topic,
            question_count=config.QUIZ_QUESTION_COUNT,
            difficulty_choice=difficulty
        )
        print(f"✅ {len(quiz_data.questions)} adet soru ve Giphy etiketleri başarıyla üretildi!", flush=True)
        print(f"📌 Yarışma Başlığı: {quiz_data.title}", flush=True)
    except Exception as e:
        print(f"\n[Hata] Soru üretilirken bir problem oluştu: {e}", flush=True)
        return

    # Soruların kısa özeti (Zorluk seviyesi etiketiyle birlikte)
    print("\n--- Hazırlanan Sorulardan İlk 3 Tanesi Örnek Olarak: ---", flush=True)
    for i, q in enumerate(quiz_data.questions[:3], 1):
        print(f"{i}. [{q.difficulty}] {q.question} (Doğru Şık: {q.options[q.correct_index]} | GIF: {q.giphy_keyword})", flush=True)
    print(f"...ve toplam {len(quiz_data.questions)} soru hazırlandı.\n", flush=True)

    # 4. Quiz.com Taslak Kaydı
    automator = QuizComAutomator(headless=headless)
    print("[2/3] Quiz.com üzerinde taslak oluşturuluyor ve GIF'ler bağlanıyor...", flush=True)
    
    try:
        draft_info = automator.create_quiz_draft(quiz_data)
    except FileNotFoundError as fnf:
        print(f"\n{fnf}", flush=True)
        return
    except Exception as e:
        print(f"\n[Hata] Quiz.com'da taslak oluşturulurken hata: {e}", flush=True)
        return

    edit_url = draft_info.get("edit_url")
    quiz_id = draft_info.get("quiz_id")

    print("\n" + "=" * 65, flush=True)
    print("🎯 QUIZ TASLAĞI BAŞARIYLA OLUŞTURULDU!", flush=True)
    print(f"Yarışma: {quiz_data.title}", flush=True)
    print(f"Soru Sayısı: {len(quiz_data.questions)} (Ayrı Slaytlar)", flush=True)
    print(f"🔗 Düzenleme Linkiniz: {edit_url}", flush=True)
    print("=" * 65, flush=True)
    print("\nİsterseniz yukarıdaki linke tarayıcıdan girip soruları, şıkları veya GIF'leri düzenleyebilirsiniz.", flush=True)

    # 5. Onay & Host Aşaması
    if not auto_host:
        print("\nOyunu başlatıp katılımcılara göndereceğiniz CANLI OYUN LİNKİNİ almak için:", flush=True)
        approval = input("👉 Oyunu başlatmak için ENTER'a basın (veya çıkmak için 'q'): ").strip().lower()
        if approval in ["q", "iptal", "cancel"]:
            print("İşlem tamamlandı. İstediğiniz zaman linke gidip manuel de başlatabilirsiniz.", flush=True)
            return

    print("\n[3/3] Canlı çok oyunculu oyun lobisi açılıyor...", flush=True)
    try:
        host_info = automator.host_live_game(quiz_id)
        
        print("\n" + "=" * 65, flush=True)
        print("🎉 OYUNUNUZ CANLI VE KATILIMA HAZIR!", flush=True)
        print(f"🚀 Canlı Katılım Linki : {host_info['join_url']}", flush=True)
        print(f"🔑 Oyun PIN Kodu       : {host_info['pin']}", flush=True)
        if host_info.get("host_url"):
            print(f"👑 Host Yönetim Ekranı : {host_info['host_url']}", flush=True)
        print("=" * 65, flush=True)
        print("\nArkadaşlarınıza katılım linkini veya PIN'i atarak hemen oynamaya başlayabilirsiniz!\n", flush=True)
    except Exception as e:
        print(f"[Hata] Canlı lobi açılırken hata oluştu: {e}", flush=True)
        print(f"Yarışmanıza şu linkten doğrudan erişebilirsiniz: {edit_url}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quiz Maker Agent - Konudan Canlı Quiz Oyununa")
    parser.add_argument("--topic", "-t", type=str, help="Hazırlanacak quiz konusu")
    parser.add_argument(
        "--difficulty", "-d",
        type=int,
        choices=range(1, 8),
        help="Zorluk seviyesi seçimi (1: Kolay, 2: Orta, 3: Zor, 4: Kolay-Orta, 5: Orta-Zor, 6: Kolay-Zor, 7: Kolay-Orta-Zor)"
    )
    parser.add_argument("--auto-host", action="store_true", help="Onay sormadan doğrudan canlı lobi açar")
    parser.add_argument("--headed", action="store_true", help="Tarayıcıyı görünür şekilde çalıştırır")
    args = parser.parse_args()

    run_quiz_agent(
        topic=args.topic,
        difficulty=args.difficulty,
        auto_host=args.auto_host,
        headless=not args.headed
    )
