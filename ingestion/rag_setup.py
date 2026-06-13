from typing import Dict, List
import csv

import chromadb


def prepare_nutrition_documents(csv_path: str) -> Dict:
    """
    Convert nutrition CSV into ChromaDB-ready documents.
    Each food item becomes a searchable document.
    """
    documents = []
    metadatas = []
    ids = []

    with open(csv_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        
        for index, row in enumerate(csv_reader):
            # Create rich document text for semantic search
            cals_per_100g = row["Cals_per100grams"].replace(" cal", "")
            kj_per_100g = row["KJ_per100grams"].replace(" kJ", "")
            
            document_text = f"""
            Food: {row['FoodItem']}
            Category: {row['FoodCategory']}
            Nutritional Information:
            - Calories: {cals_per_100g} per 100g
            - Energy: {kj_per_100g} kJ per 100g
            - Serving size reference: {row['per100grams']}

            This is a {row['FoodCategory'].lower()} food item that provides {cals_per_100g} calories per 100 grams.
            """.strip()

            # Rich metadata for filtering and exact lookups
            metadata = {
                "food_item": row["FoodItem"].lower(),
                "food_category": row["FoodCategory"].lower(),
                "calories_per_100g": (
                    float(cals_per_100g)
                    if cals_per_100g and cals_per_100g.strip()
                    else 0.0
                ),
                "kj_per_100g": (
                    float(kj_per_100g) 
                    if kj_per_100g and kj_per_100g.strip()
                    else 0.0
                ),
                "serving_info": row["per100grams"],
                # Add searchable keywords
                "keywords": f"{row['FoodItem'].lower()} {row['FoodCategory'].lower()}".replace(
                    " ", "_"
                ),
            }

            documents.append(document_text)
            metadatas.append(metadata)
            ids.append(f"food_{index}")

    return {"documents": documents, "metadatas": metadatas, "ids": ids}


def setup_nutrition_chromadb(csv_path: str, collection_name: str = "nutrition_db"):
    """
    Create and populate ChromaDB collection with nutrition data.
    """
    # Initialize ChromaDB
    client = chromadb.PersistentClient("../data/chroma")

    # Create collection (delete if exists)
    try:
        client.delete_collection(collection_name)
    except BaseException:
        pass

    collection = client.create_collection(
        name=collection_name,
        metadata={
            "description": "Nutrition database with calorie and food information"
        },
    )

    # Prepare documents
    data = prepare_nutrition_documents(csv_path)

    # Add to ChromaDB
    collection.add(
        documents=data["documents"], metadatas=data["metadatas"], ids=data["ids"]
    )

    print(
        f"Added {len(data['documents'])} food items to ChromaDB collection '{collection_name}'"
    )
    return collection


collection = setup_nutrition_chromadb("../data/calories.csv", "nutrition_db")

# Made with Bob
