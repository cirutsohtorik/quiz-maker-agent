import os
import re
import time
from typing import Dict, Any, Optional
from playwright.sync_api import sync_playwright

import config
from modules.question_generator import QuizPackage


class QuizComAutomator:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def _ensure_session(self):
        if not config.SESSION_FILE.exists():
            raise FileNotFoundError(
                f"[HATA] Oturum dosyası bulunamadı: {config.SESSION_FILE}\n"
                f"Lütfen önce 'python setup_session.py' komutunu çalıştırarak Quiz.com hesabınıza giriş yapın!"
            )

    def _close_any_open_modal(self, page):
        """
        Quiz.com'da katmanlı modalları (örn: GIPHY -> Media Chooser -> Editör)
        tüm katmanlar kapanana kadar temizler.
        """
        for _ in range(4):
            cancel_btn = page.locator("button:has-text('Cancel'):visible, button:has-text('Close'):visible")
            if cancel_btn.count() > 0:
                try:
                    cancel_btn.first.click()
                    page.wait_for_timeout(500)
                except Exception:
                    break
            else:
                break

    def create_quiz_draft(self, quiz_data: QuizPackage) -> Dict[str, Any]:
        """
        Quiz.com üzerinde yeni quiz oluşturur, 20 soruyu ve GIF'leri ekler,
        Done ile kaydeder ve kullanıcıya Düzenleme Linkini döner.
        """
        self._ensure_session()
        print(f"\n[Quiz.com] '{quiz_data.title}' başlıklı yarışma taslağı hazırlanıyor...")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                storage_state=str(config.SESSION_FILE),
                viewport={"width": 1440, "height": 900}
            )
            page = context.new_page()

            # 1. Editöre git
            page.goto(config.QUIZ_COM_NEW_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # İlk slayt için soru tipi seç (Buttons - tek doğru cevaplı çoktan seçmeli)
            try:
                page.locator("button:has-text('Buttons'):visible").first.click()
                page.wait_for_timeout(1000)
            except Exception as e:
                print(f"[Quiz.com Uyarı] İlk slayt tipi seçilemedi: {e}")

            total_questions = len(quiz_data.questions)

            for idx, q in enumerate(quiz_data.questions):
                percent = int(((idx + 1) / total_questions) * 100)
                print(f"[Quiz.com] Soru {idx+1}/{total_questions} işleniyor (%{percent}): {q.question[:45]}...", flush=True)

                # 2. ve sonraki slaytlar için alt bardaki '+' butonuna tıkla ve 'Buttons' seç
                if idx > 0:
                    try:
                        self._close_any_open_modal(page)
                        
                        # Alt bardaki yeni slayt ekleme (+) butonu
                        plus_btn = page.locator("div.bg-petrol button:has(svg), div.bg-petrol button").last
                        plus_btn.wait_for(state="visible", timeout=10000)
                        plus_btn.click()
                        page.wait_for_timeout(1000)

                        # Açılan soru tipi penceresinden 'Buttons' seç
                        buttons_btn = page.locator("button:has-text('Buttons'):visible").first
                        buttons_btn.wait_for(state="visible", timeout=10000)
                        buttons_btn.click()
                        page.wait_for_timeout(1000)
                    except Exception as e:
                        print(f"[Quiz.com Uyarı] Slayt {idx+1} eklenemedi: {e}")

                # Soru metnini yaz (textarea)
                try:
                    q_input = page.locator("textarea").first
                    q_input.fill(q.question)
                except Exception as e:
                    print(f"[Quiz.com Uyarı] Soru metni yazılamadı: {e}")

                # Şıkları yaz (inputs: 0. yeşil doğru cevap, 1,2,3 kırmızı yanlış cevaplar)
                try:
                    inputs = page.locator("input[type='text']:visible").all()
                    # Doğru cevabı ilk kutucuğa (yeşil) yaz
                    correct_answer = q.options[q.correct_index]
                    inputs[0].fill(correct_answer)

                    # Yanlış şıkları diğer kutucuklara yaz
                    wrong_answers = [opt for i, opt in enumerate(q.options) if i != q.correct_index]
                    if len(inputs) > 1 and len(wrong_answers) > 0:
                        inputs[1].fill(wrong_answers[0])
                    if len(inputs) > 2 and len(wrong_answers) > 1:
                        inputs[2].fill(wrong_answers[1])
                    if len(inputs) > 3 and len(wrong_answers) > 2:
                        inputs[3].fill(wrong_answers[2])
                except Exception as e:
                    print(f"[Quiz.com Uyarı] Şıklar yazılamadı: {e}")

                # GIPHY'den GIF bağla
                try:
                    media_btn = page.get_by_role("button", name="Add media", exact=True)
                    if media_btn.is_visible():
                        media_btn.click()
                        page.wait_for_timeout(800)

                        # GIPHY butonuna tıkla
                        for b in page.locator("button:has-text('GIPHY')").all():
                            if b.is_visible():
                                b.click()
                                break
                        page.wait_for_timeout(1000)

                        # Arama kutusuna Giphy anahtar kelimesini yaz
                        search_inp = page.locator("input[placeholder*='Search']:visible, input[type='text']:visible").first
                        if search_inp.is_visible():
                            kw = q.giphy_keyword.strip()
                            search_inp.fill(kw)
                            page.keyboard.press("Enter")
                            page.wait_for_timeout(2000)

                            # 1. Tam etiketle ara
                            gif_item = page.locator("img[src*='media']:visible, img[src*='giphy.com/media']:visible").first
                            
                            # 2. Sonuç yoksa ve çoklu kelimeyse ilk kelimeyle dene
                            if not gif_item.is_visible() and " " in kw:
                                search_inp.fill(kw.split()[0])
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(2000)
                                gif_item = page.locator("img[src*='media']:visible, img[src*='giphy.com/media']:visible").first

                            # 3. Hala sonuç yoksa genel popüler bir anahtar kelime dene
                            if not gif_item.is_visible():
                                search_inp.fill("quiz")
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(2000)
                                gif_item = page.locator("img[src*='media']:visible, img[src*='giphy.com/media']:visible").first

                            if gif_item.is_visible():
                                gif_item.click()
                                page.wait_for_timeout(1500)
                            else:
                                self._close_any_open_modal(page)
                except Exception:
                    self._close_any_open_modal(page)
                finally:
                    self._close_any_open_modal(page)

            # 2. 'Done' butonuna tıkla ve kaydet
            print("\n[Quiz.com] Tüm 20 soru eklendi. Quiz kaydediliyor ('Done')...")
            try:
                page.locator("button:has-text('Done'):visible").first.click()
                page.wait_for_timeout(4000)
            except Exception as e:
                print(f"[Quiz.com Uyarı] Done butonuna basılamadı: {e}")

            # 3. Kütüphaneden yeni oluşturulan Quiz ID'sini yakala
            quiz_id = None
            try:
                current_url = page.url
                m = re.search(r'([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})', current_url)
                if m:
                    quiz_id = m.group(1)
                else:
                    if "library" not in current_url:
                        page.goto(config.QUIZ_COM_LIBRARY_URL, wait_until="networkidle")
                    else:
                        page.wait_for_timeout(2000)
                    
                    cards = page.locator("a[href^='/']").all()
                    for c in cards:
                        href = c.get_attribute("href") or ""
                        cm = re.search(r'([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})', href)
                        if cm:
                            quiz_id = cm.group(1)
                            break
            except Exception as e:
                print(f"[Quiz.com Uyarı] Quiz ID yakalanamadı: {e}")

            if not quiz_id:
                quiz_id = "new"

            edit_url = f"{config.QUIZ_COM_BASE_URL}/edit/{quiz_id}/"
            view_url = f"{config.QUIZ_COM_BASE_URL}/{quiz_id}/"

            browser.close()

            return {
                "quiz_id": quiz_id,
                "edit_url": edit_url,
                "view_url": view_url,
                "title": quiz_data.title,
                "question_count": len(quiz_data.questions)
            }

    def host_live_game(self, quiz_id: str) -> Dict[str, Any]:
        """
        Onaylanan yarışmayı canlı çok oyunculu modda başlatır (Play Now).
        Lobi ekranındaki PIN kodu ve Canlı Katılım Linkini yakalar.
        """
        self._ensure_session()
        print(f"\n[Quiz.com] '{quiz_id}' için canlı lobi açılıyor...")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                storage_state=str(config.SESSION_FILE),
                viewport={"width": 1440, "height": 900}
            )
            page = context.new_page()

            # Quiz detay sayfasına git
            quiz_url = f"{config.QUIZ_COM_BASE_URL}/{quiz_id}/"
            page.goto(quiz_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # 'Play Now' butonuna tıkla
            try:
                play_btn = page.locator("button:has-text('Play Now'):visible").first
                if play_btn.is_visible(timeout=5000):
                    play_btn.click()
                    page.wait_for_timeout(4000)
            except Exception as e:
                print(f"[Quiz.com Uyarı] Play Now butonu tıklanamadı: {e}")

            # Ekranda 6 haneli PIN'i ara
            pin = "000000"
            try:
                body_text = page.inner_text("body")
                pin_m = re.search(r'PIN\s*([0-9]{3}\s?[0-9]{3})', body_text)
                if pin_m:
                    pin = pin_m.group(1).replace(" ", "")
                else:
                    # Alternatif PIN regex
                    pin_alt = re.search(r'PIN code:\s*\n*([0-9]{3})\s*\n*([0-9]{3})', body_text)
                    if pin_alt:
                        pin = pin_alt.group(1) + pin_alt.group(2)
                    else:
                        digits = re.findall(r'\b[0-9]{6}\b', body_text)
                        if digits:
                            pin = digits[0]
            except Exception as e:
                print(f"[Quiz.com Uyarı] PIN yakalanamadı: {e}")

            join_url = f"{config.QUIZ_COM_BASE_URL}/join/{pin}/" if pin != "000000" else f"{config.QUIZ_COM_BASE_URL}/{quiz_id}/"
            host_url = f"{config.QUIZ_COM_BASE_URL}/play/{quiz_id}/"

            print(f"[Quiz.com] Canlı Oyun Lobisi Hazır! PIN: {pin} | Katılım: {join_url}")

            browser.close()

            return {
                "pin": pin,
                "join_url": join_url,
                "host_url": host_url,
                "quiz_id": quiz_id
            }
