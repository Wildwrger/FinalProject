import random

import pandas as pd
import numpy as np
import joblib
from elasticsearch import Elasticsearch
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import re
import os

es_host = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
es = Elasticsearch([f"http://{es_host}:9200"])
# es = Elasticsearch(
#     ["http://localhost:9200"],  # Elasticsearch 서버 URL (localhost나 실제 서버 주소로 설정)
#     request_timeout=100,  # 연결 시간 초과 설정 (초 단위)
# )

def extract_ingredients(source):
    """
    재료(ingredients)와 특별 재료(special) 포함하여 추출하는 함수
    """
    ingredients = []

    # 일반 재료 추출
    for ingredient in source.get('ingredients', []):
        if 'ingredient' in ingredient:
            ingredients.append(ingredient['ingredient'])

    # special 필드 추출
    for special in source.get('special', []):
        if isinstance(special, str):
            # 숫자, 단위 제거 후 재료명만 추출
            cleaned_special = re.sub(r'[\d.]+[a-zA-Z]*', '', special).strip()
            if cleaned_special:
                ingredients.append(cleaned_special)

    return ingredients

def fetch_data_from_es(index_name, size=1000):
    """ Elasticsearch에서 레시피 데이터를 가져오는 함수 """
    query = {"query": {"match_all": {}}, "size": size}
    response = es.search(index=index_name, body=query)

    data = []
    for hit in response['hits']['hits']:
        source = hit['_source']
        recipe_id = hit['_id']  # Elasticsearch 문서의 _id 사용
        ingredients = extract_ingredients(source)
        name = source.get('name')

        # 공통 필드
        recipe_data = {
            'id': recipe_id,
            'name': name,
            'ingredients': ingredients
        }

        # 인덱스별 필드 추가
        if index_name == 'recipe_food':
            recipe_data['major'] = source.get('RCP_WAY2', '')
            recipe_data['minor'] = source.get('RCP_PAT2', '')

        elif index_name == 'recipe_cocktail':
            # abv를 따로 분리하고, major, minor를 각각 category, glass로 변경
            recipe_data['abv'] = str(source.get('abv', ''))  # abv를 따로 저장
            recipe_data['major'] = source.get('category', '')  # category를 major로 저장
            recipe_data['minor'] = source.get('glass', '')  # glass를 minor로 저장

        data.append(recipe_data)

    return pd.DataFrame(data)

def train_tfidf_model(df, category, name_path='_name.pkl', ingredient_path='_ingredient.pkl', major_path='_major.pkl',
                      minor_path='_minor.pkl', abv_path='_abv.pkl'):
    """ 재료(ingredients), 조리법(major), 음식 종류(minor)를 각각 벡터화하고 저장, abv는 칵테일에만 처리 """

    df['name_str'] = df['name'].fillna("")
    name_vectorizer = TfidfVectorizer(max_features=1000)
    name_vectorizer.fit(df['name_str'])
    joblib.dump(name_vectorizer, category + name_path)

    # 1️⃣ 재료 (ingredients) 벡터화
    df['ingredients_str'] = df['ingredients'].apply(lambda x: ' '.join(x))
    ingredient_vectorizer = TfidfVectorizer(max_features=1000)
    ingredient_vectorizer.fit(df['ingredients_str'])
    joblib.dump(ingredient_vectorizer, category + ingredient_path)

    # 2️⃣ 조리법 (major) 벡터화
    df['major_str'] = df['major'].fillna('')
    major_vectorizer = TfidfVectorizer(max_features=100)
    major_vectorizer.fit(df['major_str'])
    joblib.dump(major_vectorizer, category + major_path)

    # 3️⃣ 음식 종류 (minor) 벡터화
    df['minor_str'] = df['minor'].fillna('')
    minor_vectorizer = TfidfVectorizer(max_features=100)
    minor_vectorizer.fit(df['minor_str'])
    joblib.dump(minor_vectorizer, category + minor_path)

    # 4️⃣ abv 처리 (칼럼이 'cocktail'일 때만 처리)
    if category == "cocktail":
        abv_data = df['abv'].apply(lambda x: float(x) if x else 0).values.reshape(-1, 1)  # 수치형으로 변환
        abv_scaler = StandardScaler()  # 정규화
        abv_scaler.fit(abv_data)
        joblib.dump(abv_scaler, category + abv_path)

def load_tfidf_models(category, name_path='_name.pkl', ingredient_path='_ingredient.pkl', major_path='_major.pkl',
                      minor_path='_minor.pkl', abv_path='_abv.pkl'):
    """ 저장된 TF-IDF 및 정규화 모델을 불러오는 함수 """
    name_vectorizer = joblib.load(category + name_path)
    ingredient_vectorizer = joblib.load(category + ingredient_path)
    major_vectorizer = joblib.load(category + major_path)
    minor_vectorizer = joblib.load(category + minor_path)

    # 'cocktail' 타입일 때만 abv 모델을 불러옴
    if category == "cocktail":
        abv_scaler = joblib.load(category + abv_path)
        return name_vectorizer, ingredient_vectorizer, major_vectorizer, minor_vectorizer, abv_scaler
    else:
        return name_vectorizer, ingredient_vectorizer, major_vectorizer, minor_vectorizer, None

def train_weight(index, df, name_vectorizer, ingredient_vectorizer, major_vectorizer, minor_vectorizer,
                 abv_scaler=None,
                 weight_init_name=0.5, weight_init_ingredients=0.6, weight_init_major=0.3, weight_init_minor=0.1,
                 weight_init_abv=0.5,
                 epochs=10, lr=0.001):
    """
    릿지 회귀를 사용하여 최적의 가중치를 학습하는 함수
    """
    if index == "cocktail":
        data = pd.read_json("cocktail_test.json")
    elif index == "food":
        data = pd.read_json("food_test.json")
    else:
        return None, None, None, None

    # 초기 가중치 설정
    weight_name = weight_init_name
    weight_ingredients = weight_init_ingredients
    weight_major = weight_init_major
    weight_minor = weight_init_minor
    weight_abv = weight_init_abv

    for epoch in range(epochs):
        print(f"Epoch {epoch + 1}")
        train_data, test_data = train_test_split(data, test_size=0.2)

        for _, row in train_data.iterrows():
            liked_items = row.dropna().tolist()
            if len(liked_items) <= 1:
                continue

            idx = random.randint(0, len(liked_items) - 1)
            y = liked_items[idx]
            x = liked_items[:idx] + liked_items[idx + 1:]

            recommendations = recommend(x, df, name_vectorizer, ingredient_vectorizer,
                                        major_vectorizer, minor_vectorizer, abv_scaler,
                                        weight_name, weight_ingredients,
                                        weight_major, weight_minor, weight_abv)

            top_3_ids = [rec[0] for rec in recommendations[:3]]
            predicted_similarity = recommendations[0][1]  # 1번째 요소가 점수

            if y not in top_3_ids:
                # y의 해당 인덱스를 찾고 유사도 값들을 가져옴
                y_rec = next(rec for rec in recommendations if rec[0] == y)
                similarities = y_rec[2:]  # name, ingredient, major, minor, abv 유사도 값들

                # 유사도 기준으로 상위 2개 인덱스 선택
                top_2 = sorted(enumerate(similarities), key=lambda x: x[1], reverse=True)[:2]
                # 유사도 기준으로 하위 2개 인덱스 선택
                bottom_2 = sorted(enumerate(similarities), key=lambda x: x[1])[:2]

                # 가장 높은 유사도 2개 증가
                for idx, _ in top_2:
                    if idx == 0:
                        weight_name += lr * (1 - weight_name)
                    elif idx == 1:
                        weight_ingredients += lr * (1 - weight_ingredients)
                    elif idx == 2:
                        weight_major += lr * (1 - weight_major)
                    elif idx == 3:
                        weight_minor += lr * (1 - weight_minor)
                    elif idx == 4:
                        weight_abv += lr * (1 - weight_abv)
                for idx, _ in bottom_2:
                    if idx == 0:
                        weight_name -= lr * (weight_name - 0.01)
                    elif idx == 1:
                        weight_ingredients -= lr * (weight_ingredients - 0.01)
                    elif idx == 2:
                        weight_major -= lr * (weight_major - 0.01)
                    elif idx == 3:
                        weight_minor -= lr * (weight_minor - 0.01)
                    elif idx == 4:
                        weight_abv -= lr * (weight_abv - 0.01)

            # 추천 점수가 100을 초과하면 모든 가중치를 감소
            if predicted_similarity > 100:
                scale_factor = 100 / predicted_similarity  # 모든 weight를 이 비율로 조정
                weight_name *= scale_factor
                weight_ingredients *= scale_factor
                weight_major *= scale_factor
                weight_minor *= scale_factor
                weight_abv *= scale_factor

                # 최소값 보정 (너무 작아지는 걸 방지)
                min_weight = 0.01
                weight_name = max(weight_name, min_weight)
                weight_ingredients = max(weight_ingredients, min_weight)
                weight_major = max(weight_major, min_weight)
                weight_minor = max(weight_minor, min_weight)
                weight_abv = max(weight_abv, min_weight)

                print(f"Adjusted Weights due to high similarity score: {predicted_similarity}")

            # 추천 점수가 50 이하일 때 모든 가중치를 증가
            elif predicted_similarity <= 50:
                scale_factor = 1 + (80 - predicted_similarity) / 100  # 목표는 80점으로 조정
                weight_name *= scale_factor
                weight_ingredients *= scale_factor
                weight_major *= scale_factor
                weight_minor *= scale_factor
                weight_abv *= scale_factor

                # 최대값 보정 (너무 커지는 걸 방지)
                max_weight = 1
                weight_name = min(weight_name, max_weight)
                weight_ingredients = min(weight_ingredients, max_weight)
                weight_major = min(weight_major, max_weight)
                weight_minor = min(weight_minor, max_weight)
                weight_abv = min(weight_abv, max_weight)

                print(f"Adjusted Weights due to low similarity score: {predicted_similarity}")
        print(f"Updated Weights - Name: {weight_name:.4f}, Ingredients: {weight_ingredients:.4f}, "
              f"Major: {weight_major:.4f}, Minor: {weight_minor:.4f}, ABV: {weight_abv:.4f}")

    # 최종 가중치 반환
    return weight_name, weight_ingredients, weight_major, weight_minor, weight_abv


def recommend(user_likes, df, name_vectorizer, ingredient_vectorizer, major_vectorizer, minor_vectorizer, abv_scaler,
              weight_name, weight_ingredient, weight_major, weight_minor, weight_abv):
    recommendations = []

    for _, row in df.iterrows():
        if row['id'] in user_likes:  # user_like 목록에 있는 아이디는 제외
            continue  # 자기 자신 제외

        total_name_similarity = 0
        total_ingredient_similarity = 0
        total_major_similarity = 0
        total_minor_similarity = 0
        total_abv_similarity = 0

        # 모든 user_like에 대해 유사도를 계산
        for user_like_id in user_likes:
            liked_recipe_row = df[df['id'] == user_like_id]
            if liked_recipe_row.empty:
                continue  # ID가 없으면 건너뛰기

            # 사용자가 좋아한 레시피 벡터화
            liked_name_vec = name_vectorizer.transform(liked_recipe_row['name_str'])
            liked_ingredient_vec = ingredient_vectorizer.transform(liked_recipe_row['ingredients_str'])
            liked_major_vec = major_vectorizer.transform(liked_recipe_row['major_str'])
            liked_minor_vec = minor_vectorizer.transform(liked_recipe_row['minor_str'])
            liked_abv = liked_recipe_row['abv'].values.reshape(-1, 1) if 'abv' in liked_recipe_row.columns else None

            if abv_scaler is not None and liked_abv is not None:
                liked_abv = abv_scaler.transform(liked_abv)

            # 비교 대상 레시피 벡터화
            name_vec = name_vectorizer.transform([row['name_str']])
            ingredient_vec = ingredient_vectorizer.transform([row['ingredients_str']])
            maj_vec = major_vectorizer.transform([row['major_str']])
            min_vec = minor_vectorizer.transform([row['minor_str']])
            abv = row['abv'] if 'abv' in row else None
            abv = np.array(abv).reshape(-1, 1) if abv is not None else None

            if abv_scaler is not None and abv is not None:
                abv = abv_scaler.transform(abv)

            # 유사도 계산 (코사인 유사도 사용)
            name_similarity = cosine_similarity(liked_name_vec, name_vec)[0][0]
            ingredient_similarity = cosine_similarity(liked_ingredient_vec, ingredient_vec)[0][0]
            major_similarity = cosine_similarity(liked_major_vec, maj_vec)[0][0]
            minor_similarity = cosine_similarity(liked_minor_vec, min_vec)[0][0]

            # abv 유사도 계산 (스칼라 값 차이로 계산)
            abv_similarity = 1 - abs(liked_abv - abv) if abv is not None else 0

            # abv_similarity가 배열이 아닌지 확인하고, 단일 값으로 변환
            if isinstance(abv_similarity, np.ndarray):
                abv_similarity = abv_similarity[0][0]

            # 유사도 항목을 더함
            total_name_similarity += name_similarity
            total_ingredient_similarity += ingredient_similarity
            total_major_similarity += major_similarity
            total_minor_similarity += minor_similarity
            total_abv_similarity += abv_similarity

        # 평균 유사도 계산
        avg_name_similarity = total_name_similarity / len(user_likes)
        avg_ingredient_similarity = total_ingredient_similarity / len(user_likes)
        avg_major_similarity = total_major_similarity / len(user_likes)
        avg_minor_similarity = total_minor_similarity / len(user_likes)
        avg_abv_similarity = total_abv_similarity / len(user_likes)

        # 평균 유사도를 기반으로 최종 유사도 계산
        total_similarity = (
                avg_name_similarity * weight_name +
                avg_ingredient_similarity * weight_ingredient +
                avg_major_similarity * weight_major +
                avg_minor_similarity * weight_minor +
                avg_abv_similarity * weight_abv
        )

        # 점수화 (100을 곱해 점수화)
        total_similarity_score = round(float(total_similarity) * 100)  # 100을 곱해 점수화
        recommendations.append((row['id'], total_similarity_score, avg_name_similarity, avg_ingredient_similarity, avg_major_similarity, avg_minor_similarity, avg_abv_similarity))  # 레시피 아이디와 점수 저장

    # 추천 목록을 점수 내림차순으로 정렬
    recommendations = sorted(recommendations, key=lambda x: x[1], reverse=True)
    return recommendations


def recommend_recipe(user_likes, df, name_vectorizer, ingredient_vectorizer, major_vectorizer, minor_vectorizer, abv_scaler=None, top_n=3, weight_name=0.5, weight_ingredient=0.6, weight_major=0.3, weight_minor=0.1, weight_abv=0.5):
    """
    사용자 좋아요 기반으로 레시피 추천하는 함수
    - 재료(ingredients), 조리법(major), 음식 종류(minor), abv 유사도를 따로 계산
    - 각 요소에 가중치를 적용하여 최종 유사도를 계산
    """
    recommendations = recommend(user_likes, df, name_vectorizer, ingredient_vectorizer, major_vectorizer, minor_vectorizer, abv_scaler, weight_name, weight_ingredient, weight_major, weight_minor, weight_abv)
    # id와 total_similarity_score만 반환하도록 필터링
    recommendations = [(recipe_id, score) for recipe_id, score, *_ in recommendations]

    # 추천 결과를 유사도 순으로 정렬하고, 상위 N개만 반환

    return recommendations[:top_n]  # 상위 N개 추천


# 현재 파일에서만 실행되도록 조건 추가
if __name__ == "__main__":
    dataframe = fetch_data_from_es("recipe_food")
    train_tfidf_model(dataframe, "food")
    name_vec, ing_vec, major_vec, minor_vec, abv_sca = load_tfidf_models("food")
    name_weight, ing_weight, major_weight, minor_weight, abv_weight = train_weight("food", dataframe, name_vec, ing_vec, major_vec, minor_vec, abv_sca)
    print( name_weight, ing_weight, major_weight, minor_weight, abv_weight )
    recommends = recommend_recipe(['VDoqapUBcJinAtT_JMIS'], dataframe, name_vec, ing_vec, major_vec, minor_vec, abv_sca, 3 , name_weight, ing_weight, minor_weight, abv_weight)
    print(recommends)
