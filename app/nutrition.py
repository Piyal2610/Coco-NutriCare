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


MATERNAL_TARGETS = {
    "First": {"calories": 2000, "protein_g": 71, "iron_mg": 27, "calcium_mg": 1000, "folate_mcg": 600},
    "Second": {"calories": 2340, "protein_g": 71, "iron_mg": 27, "calcium_mg": 1000, "folate_mcg": 600},
    "Third": {"calories": 2450, "protein_g": 71, "iron_mg": 27, "calcium_mg": 1000, "folate_mcg": 600},
}

MATERNAL_FOODS = [
    ("Breakfast", "Ruti with vegetables", {"whole_grain"}, None),
    ("Breakfast", "Boiled egg (fully cooked)", {"protein"}, None),
    ("Breakfast", "Banana", set(), None),
    ("Breakfast", "Chira with yogurt", {"calcium_rich"}, None),
    ("Breakfast", "Suji halwa", {"high_sugar"}, "Oats porridge without sugar"),
    ("Breakfast", "Milk tea with sugar", {"high_sugar"}, "Warm milk without sugar"),
    ("Lunch", "White rice", {"refined_carb"}, "Brown or red rice"),
    ("Lunch", "Dal (lentils)", {"iron_rich"}, None),
    ("Lunch", "Lal shak / spinach", {"iron_rich"}, None),
    ("Lunch", "Small fish curry (mola, kachki)", {"iron_rich", "calcium_rich"}, None),
    ("Lunch", "Chicken curry", {"protein"}, None),
    ("Lunch", "Shutki bhorta", {"high_salt"}, "Fresh fish bhorta"),
    ("Dinner", "Ruti", {"whole_grain"}, None),
    ("Dinner", "Mixed vegetable curry", set(), None),
    ("Dinner", "Egg curry", {"protein"}, None),
    ("Dinner", "Lean beef curry", {"iron_rich", "protein"}, None),
    ("Dinner", "Polao", {"refined_carb"}, "Vegetable khichuri with brown rice"),
    ("Snack", "Guava or orange", {"vitamin_c"}, None),
    ("Snack", "Roasted chola (chickpeas)", {"iron_rich"}, None),
    ("Snack", "Tok doi (plain yogurt)", {"calcium_rich"}, None),
    ("Snack", "Mishti (sweets)", {"high_sugar"}, "Fresh fruit salad"),
    ("Snack", "Chanachur / chips", {"high_salt"}, "Unsalted roasted peanuts"),
    ("Snack", "Achar (pickle)", {"high_salt"}, "Cucumber salad with lemon"),
]

CONDITION_RULES = {
    "gestational_diabetes": {
        "avoid": {"high_sugar", "refined_carb"},
        "note": "Gestational diabetes: whole grains are used instead of white rice and sugar; eat small meals at regular times.",
    },
    "hypertension": {
        "avoid": {"high_salt"},
        "note": "Hypertension: salty foods such as pickles, dried fish and chanachur are replaced; avoid adding extra salt.",
    },
    "anemia": {
        "prefer": {"iron_rich"},
        "note": "Anemia: iron-rich foods come first. Eat them with vitamin C fruit and avoid tea or coffee within an hour of meals.",
    },
    "thyroid": {
        "note": "Thyroid disorder: use iodised salt and take your thyroid medicine at the prescribed time, away from iron or calcium tablets.",
    },
}

GENERAL_PREGNANCY_NOTES = [
    "Eat only fully cooked eggs, meat and fish, and boiled or pasteurised milk.",
    "Keep tea and coffee moderate (under 200 mg caffeine a day) and drink plenty of safe water.",
    "Take iron, folic acid and calcium supplements only as your doctor prescribes.",
]


def build_maternal_plan(profile, seed=None):
    keys = profile.condition_keys
    avoid = set().union(*(CONDITION_RULES[k].get("avoid", set()) for k in keys))
    prefer = set().union(*(CONDITION_RULES[k].get("prefer", set()) for k in keys))
    rng = random.Random(seed)
    meals = {}
    swaps = []
    avoided = []
    for meal in MEALS:
        options = []
        swapped_from = {}
        for slot, name, tags, swap in MATERNAL_FOODS:
            if slot != meal:
                continue
            if tags & avoid:
                avoided.append(name)
                if swap:
                    options.append((swap, False))
                    swapped_from[swap] = name
                continue
            options.append((name, bool(tags & prefer)))
        rng.shuffle(options)
        options.sort(key=lambda option: not option[1])
        chosen = [name for name, _ in options[:ITEMS_PER_MEAL]]
        meals[meal] = chosen
        swaps += [{"from": swapped_from[name], "to": name} for name in chosen if name in swapped_from]
    return {
        "type": "maternal",
        "week": profile.pregnancy_week,
        "trimester": profile.trimester,
        "conditions": profile.condition_labels,
        "targets": MATERNAL_TARGETS[profile.trimester],
        "meals": meals,
        "avoided": avoided,
        "swaps": swaps,
        "notes": [CONDITION_RULES[k]["note"] for k in keys] + GENERAL_PREGNANCY_NOTES,
    }


def create_maternal_recommendation(profile, seed=None):
    plan = build_maternal_plan(profile, seed)
    recommendation = Recommendation(maternal_id=profile.id, plan_details=json.dumps(plan))
    db.session.add(recommendation)
    db.session.commit()
    return recommendation