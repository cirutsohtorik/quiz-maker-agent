# 🎮 Quiz-Maker-Agent: Otonom Yarışma ve Canlı Lobi Ajanı

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-tested-green.svg)](https://playwright.dev/)
[![Gemini API](https://img.shields.io/badge/Google%20Gemini-Flash%203.1-orange.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Quiz-Maker-Agent**, dilediğiniz herhangi bir konu başlığını alarak saniyeler içinde **20 soruluk interaktif yarışma** üreten, her soruya en uygun **GIF animasyonlarını** bağlayan, **Quiz.com** üzerinde otomatik taslak oluşturan ve onayınızla **canlı çok oyunculu oyun odasını (PIN ve Katılım Linki)** teslim eden otonom bir AI ajanıdır.

---

## 📌 Sistem Gereksinimleri & Kısıtlamalar

Bu projeyi çalıştırmadan önce lütfen aşağıdaki kısıtlamaları ve gereksinimleri göz önünde bulundurun:

1. **LLM Motoru:** Yalnızca **Google Gemini API** desteklenmektedir (Google AI Studio üzerinden [ücretsiz API anahtarı](https://aistudio.google.com/) alabilirsiniz).
2. **Tarayıcı:** Web otomasyonu için **Playwright Chromium** kullanılır (varsayılan olarak arka planda/headless çalışır; kullanıcı bilgisayarına ek bir tarayıcı kurmaya gerek yoktur).
3. **Platform:** Yarışmaların barındırılması için **[Quiz.com](https://quiz.com/)** hesabı gereklidir (ilk çalıştırmada 1 kez giriş yapılması yeterlidir).
4. **Soru Formatı:** Her yarışma için tam 20 soru, 4 şıklı buton modu (tek doğru cevap) ve otomatik GIPHY entegrasyonu oluşturulur.

---

## 🚀 3 Adımda Hızlı Kurulum

### 1. Depoyu Klonlayın ve Bağımlılıkları Yükleyin
```bash
git clone https://github.com/cirutsohtorik/quiz-maker-agent.git
cd quiz-maker-agent

pip install -r requirements.txt
playwright install chromium
```

### 2. Çevre Değişkenlerini Ayarlayın
`.env.example` dosyasını kopyalayarak `.env` adıyla kaydedin ve Gemini API anahtarınızı girin:
```bash
cp .env.example .env
```
*(Eğer `.env` dosyasını elle oluşturmazsanız, ajanı ilk kez çalıştırdığınızda konsol üzerinden sizden otomatik olarak isteyecektir.)*

### 3. Ajanı Çalıştırın!
```bash
python quiz_agent.py
```
- İlk çalıştırmada Quiz.com oturumunuz yoksa otomatik olarak bir Chrome penceresi açılır ve giriş yapmanız istenir.
- Ardından dilediğiniz konuyu yazarak arkanıza yaslanabilirsiniz!

---

## 🎯 Kullanım Seçenekleri (CLI)

### A) İnteraktif Mod (Önerilen)
```bash
python quiz_agent.py
```
Ajan sizden konuyu sorar, soruları ve GIF'leri hazırlar, Quiz.com'da taslağı açar ve kontrol etmeniz için düzenleme linkini sunar.

### B) Tek Satırda Konu Belirterek Çalıştırma
```bash
python quiz_agent.py --topic "90'lar Türkçe Pop ve Rock"
```

### C) Onay Adımını Atlayıp Doğrudan Canlı Lobi Açma
```bash
python quiz_agent.py --topic "Marvel ve DC Evreni" --auto-host
```

### D) Tarayıcı Hareketlerini Ekranda Canlı İzleme (Headed Mod)
```bash
python quiz_agent.py --headed
```

---

## 🔄 İki Aşamalı Kontrol Akışı (Edit & Approval Gate)

1. **Taslak İnceleme Aşaması:**  
   Sorular üretilip Quiz.com'a yüklendikten sonra ajan size özel düzenleme linkini teslim eder:  
   `🔗 Düzenleme Linkiniz: https://quiz.com/edit/<quizId>/`  
   Dilerseniz linke tıklayarak soruları, şıkları veya GIF'leri web arayüzünden manuel olarak kontrol edebilirsiniz.

2. **Canlı Lobi & PIN Teslimi:**  
   Terminalde **ENTER** tuşuna bastığınız anda canlı oyun odası aktive edilir:  
   `🚀 Canlı Katılım Linki: https://quiz.com/join/<PIN>/`  
   `🔑 Oyun PIN Kodu: <PIN>`  
   `👑 Host Yönetim Ekranı: https://quiz.com/play/<quizId>/`

---

## 🔒 Güvenlik ve Gizlilik (Security & Privacy)

- **API Anahtarı ve Oturum Güvenliği:** Kişisel Gemini API anahtarınız (`.env`) ve Quiz.com giriş çerezleriniz (`session.json`) `.gitignore` tarafından **kesinlikle dışlanmıştır**. Git commit'lerine asla dahil edilmez.
- **Şifresiz Oturum:** Şifrenizi hiçbir koda veya ajana vermeniz gerekmez. Tarayıcı penceresi üzerinden doğrudan Quiz.com arayüzünde giriş yapılır.

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) altında açık kaynak olarak sunulmuştur.
