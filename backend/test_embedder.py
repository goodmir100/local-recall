import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer

print("1. Загрузка мультиязычной модели (paraphrase-multilingual-MiniLM-L12-v2)...")
# Переходим на мультиязычную модель (~470 МБ)
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

docs = [
    {"id": 1, "app": "Chrome", "text": "Купить авиабилеты Москва Сочи недорого отель бронирование"},
    {"id": 2, "app": "VS Code", "text": "import torch.nn as nn class NeuralNet(nn.Module): def __init__"},
    {"id": 3, "app": "Telegram", "text": "Привет! Когда пойдем играть в футбол на выходных?"}
]

print("2. Генерация векторных эмбеддингов...")
embeddings = model.encode([doc["text"] for doc in docs])

print("3. Проверка поиска по смыслу (Cosine Similarity)...")
user_query = "поездка на море и перелет"
query_vec = model.encode(user_query)

similarities = np.dot(embeddings, query_vec) / (
    np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_vec)
)

best_match_idx = np.argmax(similarities)
best_doc = docs[best_match_idx]

print(f"\n[Поисковый запрос]: '{user_query}'")
print(f"[Лучший результат]: App: {best_doc['app']} | Текст: {best_doc['text']}")
print(f"[Релевантность]: {similarities[best_match_idx]:.4f}")

if best_doc["id"] == 1:
    print("\n🔥 Отлично! Мультиязычный векторный поиск работает правильно!")