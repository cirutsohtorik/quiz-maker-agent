import os
import sys
import time

# Windows terminal UTF-8 encoding fix
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from typing import List, Dict, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

import config


class QuestionItem(BaseModel):
    question: str = Field(description="Soru metni (Türkçe, anlaşılır, eğlenceli)")
    options: List[str] = Field(description="Tam 4 adet benzersiz şık/seçenek")
    correct_index: int = Field(description="Doğru şıkkın indeksi (0, 1, 2 veya 3)")
    giphy_keyword: str = Field(description="Bu soru için en uygun, komik veya ikonik GIF'i bulmak için 2-3 kelimelik İngilizce arama etiketi (örn: 'football celebration', 'shocked face', 'epic fail')")
    time_limit: int = Field(default=20, description="Soru için süre (saniye cinsinden, varsayılan 20)")
    difficulty: str = Field(default="Orta", description="Sorunun zorluk seviyesi: 'Kolay', 'Orta' veya 'Zor'")


class QuizPackage(BaseModel):
    title: str = Field(description="Yarışma başlığı (kısa ve dikkat çekici)")
    description: str = Field(description="Yarışma açıklaması")
    topic: str = Field(description="Kullanıcının verdiği orijinal konu")
    questions: List[QuestionItem] = Field(description="Tam 20 adet soru listesi")


# 7 Farklı Zorluk Kombinasyonu ve Dağılım Kuralları
DIFFICULTY_PRESETS: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "Kolay",
        "description": "20 Kolay Soru",
        "prompt_instruction": "Tüm sorular 'Kolay' seviyede olmalıdır. Temel, herkesin rahatça ve keyifle yanıtlayabileceği genel/popüler bilgiler içermelidir."
    },
    2: {
        "name": "Orta",
        "description": "20 Orta Soru",
        "prompt_instruction": "Tüm sorular 'Orta' seviyede olmalıdır. Biraz düşündüren, dengeli ve rekabetçi yarışma soruları olmalıdır."
    },
    3: {
        "name": "Zor",
        "description": "20 Zor Soru",
        "prompt_instruction": "Tüm sorular 'Zor' seviyede olmalıdır. Derin bilgi, dikkat ve uzmanlık gerektiren iddialı sorular olmalıdır."
    },
    4: {
        "name": "Kolay - Orta",
        "description": "10 Kolay + 10 Orta Soru",
        "prompt_instruction": (
            "Tam 10 adet 'Kolay' ve tam 10 adet 'Orta' seviye soru üretilmelidir (Toplam 20 soru). "
            "ÖNEMLİ KURAL: Aynı zorluktaki sorular ASLA arka arkaya gelmemelidir! "
            "Zorlukları 'Kolay', 'Orta', 'Kolay', 'Orta'... şeklinde dönüşümlü sırayla üret."
        )
    },
    5: {
        "name": "Orta - Zor",
        "description": "10 Orta + 10 Zor Soru",
        "prompt_instruction": (
            "Tam 10 adet 'Orta' ve tam 10 adet 'Zor' seviye soru üretilmelidir (Toplam 20 soru). "
            "ÖNEMLİ KURAL: Aynı zorluktaki sorular ASLA arka arkaya gelmemelidir! "
            "Zorlukları 'Orta', 'Zor', 'Orta', 'Zor'... şeklinde dönüşümlü sırayla üret."
        )
    },
    6: {
        "name": "Kolay - Zor",
        "description": "10 Kolay + 10 Zor Soru",
        "prompt_instruction": (
            "Tam 10 adet 'Kolay' ve tam 10 adet 'Zor' seviye soru üretilmelidir (Toplam 20 soru). "
            "ÖNEMLİ KURAL: Aynı zorluktaki sorular ASLA arka arkaya gelmemelidir! "
            "Zorlukları 'Kolay', 'Zor', 'Kolay', 'Zor'... şeklinde dönüşümlü sırayla üret."
        )
    },
    7: {
        "name": "Kolay - Orta - Zor",
        "description": "7 Kolay + 7 Orta + 6 Zor Soru",
        "prompt_instruction": (
            "Tam 7 adet 'Kolay', tam 7 adet 'Orta' ve tam 6 adet 'Zor' seviye soru üretilmelidir (Toplam 20 soru). "
            "ÖNEMLİ KURAL: Aynı zorluktaki sorular ASLA arka arkaya gelmemelidir! "
            "Zorlukları döngüsel olarak 'Kolay', 'Orta', 'Zor', 'Kolay', 'Orta', 'Zor'... şeklinde dönüşümlü sırayla üret."
        )
    }
}


def interleave_questions_by_difficulty(questions: List[QuestionItem]) -> List[QuestionItem]:
    """
    Soruları, ardışık olarak aynı zorluk seviyesinde soru gelmeyecek şekilde
    akıllıca harmanlar (anti-clustering interleaving).
    """
    if len(questions) <= 1:
        return questions

    # Zorluk seviyelerini standartlaştır ve grupla
    buckets: Dict[str, List[QuestionItem]] = {}
    for q in questions:
        diff = (getattr(q, "difficulty", None) or "Orta").strip().capitalize()
        if diff not in ["Kolay", "Orta", "Zor"]:
            diff = "Orta"
        q.difficulty = diff
        buckets.setdefault(diff, []).append(q)

    # Eğer sadece 1 çeşit zorluk varsa sıralamayı değiştirmeye gerek yok
    if len(buckets) <= 1:
        return questions

    preferred_order = ["Kolay", "Orta", "Zor"]
    active_keys = [k for k in preferred_order if k in buckets and buckets[k]]
    for k in buckets:
        if k not in active_keys and buckets[k]:
            active_keys.append(k)

    result: List[QuestionItem] = []
    total_count = len(questions)
    rr_idx = 0

    while len(result) < total_count:
        last_diff = result[-1].difficulty if result else None
        candidates = [k for k in active_keys if buckets[k] and k != last_diff]

        if not candidates:
            candidates = [k for k in active_keys if buckets[k]]
            if not candidates:
                break
            result.append(buckets[candidates[0]].pop(0))
            continue

        # Sıkışmayı önlemek için kalan eleman sayısı en yüksek olan adayı seç
        max_rem = max(len(buckets[k]) for k in candidates)
        best_candidates = [k for k in candidates if len(buckets[k]) == max_rem]

        chosen_key = None
        for step in range(len(active_keys)):
            candidate_key = active_keys[(rr_idx + step) % len(active_keys)]
            if candidate_key in best_candidates:
                chosen_key = candidate_key
                rr_idx = (rr_idx + step + 1) % len(active_keys)
                break

        if not chosen_key:
            chosen_key = candidates[0]

        result.append(buckets[chosen_key].pop(0))

    return result


# Alternatif model zinciri (Biri meşgul olduğunda diğeri anında devreye girer)
CANDIDATE_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.8-flash",
    "gemini-3.7-flash"
]


def generate_quiz_questions(
    topic: str,
    question_count: int = 20,
    difficulty_choice: int = 4,
    language: str = "tr"
) -> QuizPackage:
    """
    Verilen konudan Gemini API kullanarak seçilen zorluk dağılımına uygun 20 adet yapılandırılmış
    soru ve GIF etiketleri üretir. Soruları peş peşe aynı zorluk gelmeyecek şekilde harmanlar.
    """
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    
    preset = DIFFICULTY_PRESETS.get(difficulty_choice, DIFFICULTY_PRESETS[4])

    prompt = f"""
Sen dünya standartlarında bir Quiz Master ve soru yazarısın.
Kullanıcının belirlediği konu: "{topic}"
Seçilen Zorluk Derecesi: {preset['name']} ({preset['description']})

GÖREV:
Bu konuyla ilgili tam {question_count} adet çoktan seçmeli yarışma sorusu hazırla.

ZORLUK VE DAĞILIM KURALLARI:
{preset['prompt_instruction']}
- Her soru için `difficulty` alanını kesinlikle 'Kolay', 'Orta' veya 'Zor' olarak ata.

GENEL KURALLAR:
1. Dil: Kesinlikle {language.upper()} (Türkçe) olmalı.
2. Şıklar: Her soru için tam 4 şık (A, B, C, D) olmalı. Şıklar kafa karıştırmayacak şekilde net olmalı.
3. Doğru Cevap: `correct_index` değeri mutlaka doğru cevabın 0-tabanlı indeksini (0, 1, 2 veya 3) göstermeli.
4. Giphy Etiketi (`giphy_keyword`): Her soru için sahneye veya duyguya uygun, GIPHY'de popüler sonuç verecek 1-2 kelimelik basit İNGİLİZCE anahtar kelime yaz (Örn: 'money', 'celebration', 'math', 'confused', 'win', 'thinking', 'stress', 'office', 'happy').
5. Toplam Soru Sayısı: İstisnasız tam {question_count} adet soru üretilmelidir.
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
                
                # Soruları ardışık aynı zorluk gelmeyecek şekilde harmanla
                quiz_data.questions = interleave_questions_by_difficulty(quiz_data.questions)
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

