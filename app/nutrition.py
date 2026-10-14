import json
import random
from app.extensions import db
from app.models import Recommendation

MEALS = ("Breakfast", "Lunch", "Dinner", "Snack")
ITEMS_PER_MEAL = 3

AGE_TARGETS = [
    (6, 11, {"calories": 750, "protein_g": 11, "iron_mg": 11, "calcium_mg": 260}),
    (12, 47, {"calories": 1000, "protein_g": 13, "iron_mg": 7, "calcium_mg": 700}),
    (48, 107, {"calories": 1400, "protein_g": 19, "iron_mg": 10, "calcium_mg": 1000}),
    (108, 167, {"calories": 1800, "protein_g": 34, "iron_mg": 8, "calcium_mg": 1300}),
]

FOODS = [
    ("Breakfast", "Boiled egg", ("Egg",), 6),
    ("Breakfast", "Banana", (), 6),
    ("Breakfast", "Suji porridge", ("Wheat", "Milk"), 6),
    ("Breakfast", "Milk", ("Milk",), 12),
    ("Breakfast", "Chira with banana", (), 12),
    ("Breakfast", "Roti", ("Wheat",), 12),
    ("Lunch", "Rice", (), 6),
    ("Lunch", "Dal (lentils)", (), 6),
    ("Lunch", "Fish curry", ("Fish",), 6),
    ("Lunch", "Chicken curry", (), 6),
    ("Lunch", "Mixed vegetables", (), 6),
    ("Lunch", "Shrimp curry", ("Shellfish",), 12),
    ("Dinner", "Vegetable khichuri", (), 6),
    ("Dinner", "Egg khichuri", ("Egg",), 6),
    ("Dinner", "Chicken soup", (), 6),
    ("Dinner", "Roti with vegetables", ("Wheat",), 12),
    ("Snack", "Seasonal fruit", (), 6),
    ("Snack", "Yogurt (doi)", ("Milk",), 6),
    ("Snack", "Boiled chickpeas", (), 12),
    ("Snack", "Peanut butter toast", ("Peanut", "Wheat"), 12),
    ("Snack", "Nut mix", ("Tree nuts",), 48),
    ("Snack", "Sesame laddu", ("Sesame",), 48),
]

FOOD_ALLERGENS = {name: set(allergens) for _, name, allergens, _ in FOODS}


def targets_for(age_months):
    for start, end, targets in AGE_TARGETS:
        if start <= age_months <= end:
            return targets
    return None


def build_plan(child, seed=None):
    age = child.age_months
    if age < 6:
        return {"age_months": age, "breastfeeding_only": True, "targets": None, "meals": {}, "filtered": []}

    avoid = {allergy.allergen for allergy in child.allergies}
    rng = random.Random(seed)
    meals = {}
    filtered = set()
    for meal in MEALS:
        options = []
        for slot, name, allergens, min_months in FOODS:
            if slot != meal or age < min_months:
                continue
            blocked = avoid.intersection(allergens)
            if blocked:
                filtered.update(blocked)
                continue
            options.append(name)
        meals[meal] = rng.sample(options, min(ITEMS_PER_MEAL, len(options)))

    return {
        "age_months": age,
        "breastfeeding_only": False,
        "targets": targets_for(age),
        "meals": meals,
        "filtered": sorted(filtered),
    }


def create_recommendation(child, seed=None):
    plan = build_plan(child, seed)
    recommendation = Recommendation(child=child, plan_details=json.dumps(plan))
    db.session.add(recommendation)
    db.session.commit()
    return recommendation
    if cross_check(plan, child):
        raise ValueError("Generated plan contains an allergen")


def cross_check(plan, child):
    avoid = {allergy.allergen for allergy in child.allergies}
    conflicts = []
    for meal, items in (plan or {}).get("meals", {}).items():
        for item in items:
            hit = avoid.intersection(FOOD_ALLERGENS.get(item, set()))
            if hit:
                conflicts.append({"meal": meal, "item": item, "allergens": sorted(hit)})
    return conflicts   