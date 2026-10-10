import os
import sys
import time

# Windows terminal UTF-8 encoding fix
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

import config


class QuestionItem(BaseModel):
    question: str = Field(description="Soru metni (Türkçe, anlaşılır, eğlenceli ve basit-orta seviye)")
    options: List[str] = Field(description="Tam 4 adet benzersiz şık/seçenek")
    correct_index: int = Field(description="Doğru şıkkın indeksi (0, 1, 2 veya 3)")
    giphy_keyword: str = Field(description="Bu soru için en uygun, komik veya ikonik GIF'i bulmak için 2-3 kelimelik İngilizce arama etiketi (örn: 'football celebration', 'shocked face', 'epic fail')")
    time_limit: int = Field(default=20, description="Soru için süre (saniye cinsinden, varsayılan 20)")


class QuizPackage(BaseModel):
    title: str = Field(description="Yarışma başlığı (kısa ve dikkat çekici)")
    description: str = Field(description="Yarışma açıklaması")
    topic: str = Field(description="Kullanıcının verdiği orijinal konu")
    questions: List[QuestionItem] = Field(description="Tam 20 adet soru listesi")


# Alternatif model zinciri (Biri meşgul olduğunda diğeri anında devreye girer)
CANDIDATE_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.8-flash",
    "gemini-3.7-flash"
]


def generate_quiz_questions(topic: str, question_count: int = 20, language: str = "tr") -> QuizPackage:
    """
    Verilen konudan Gemini API kullanarak 20 adet yapılandırılmış soru ve GIF etiketleri üretir.
    503 UNAVAILABLE veya aşırı yoğunluk durumunda otomatik retry ve alternatif model geçişi yapar.
    """
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    
    prompt = f"""
Sen dünya standartlarında bir Quiz Master ve soru yazarısın.
Kullanıcının belirlediği konu: "{topic}"

GÖREV:
Bu konuyla ilgili tam {question_count} adet çoktan seçmeli yarışma sorusu hazırla.

KURALLAR:
1. Dil: Kesinlikle {language.upper()} (Türkçe) olmalı.
2. Zorluk Derecesi: %60 Basit, %40 Orta seviye olmalı. Sorular ne aşırı kolay ne de kimsenin bilemeyeceği kadar uç detay olmamalı; keyifli ve rekabetçi olmalı.
3. Şıklar: Her soru için tam 4 şık (A, B, C, D) olmalı. Şıklar kafa karıştırmayacak şekilde net olmalı.
4. Doğru Cevap: `correct_index` değeri mutlaka doğru cevabın 0-tabanlı indeksini (0, 1, 2 veya 3) göstermeli.
5. Giphy Etiketi (`giphy_keyword`): Her soru için sahneye veya duyguya uygun, GIPHY'de popüler sonuç verecek 1-2 kelimelik basit İNGİLİZCE anahtar kelime yaz (Örn: 'money', 'celebration', 'math', 'confused', 'win', 'thinking', 'stress', 'office', 'happy').
6. Toplam Soru Sayısı: İstisnasız tam {question_count} adet soru üretilmelidir.
"""

    last_error = None
    for model_name in CANDIDATE_MODELS:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=QuizPackage,
                        temperature=0.7,
                    ),
                )
                result_json = response.text
                quiz_data = QuizPackage.model_validate_json(result_json)
                return quiz_data
            except Exception as e:
                err_str = str(e)
                last_error = e
                # 503 yoğunluk veya geçici hata varsa
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                    print(f"[{model_name} yoğunluk yaşıyor, 2 sn bekleniyor... (Deneme {attempt+1})]")
                    time.sleep(2)
                else:
                    print(f"[{model_name} denenirken alternatif modele geçiliyor...]")
                    break

    raise RuntimeError(f"Tüm Gemini modelleri denendi ancak soru üretilemedi: {last_error}")
