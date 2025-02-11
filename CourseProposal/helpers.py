import json
import re
import sys

def validate_knowledge_and_ability():
    try:
        # Read data from the JSON file
        with open('ensemble_output.json', 'r', encoding='utf-8') as file:
            data = json.load(file)

        # Extract Knowledge and Ability factors from the data
        knowledge_factors = set([k.split(":")[0].strip() for k in data['Learning Outcomes']['Knowledge']])
        ability_factors = set([a.split(":")[0].strip() for a in data['Learning Outcomes']['Ability']])

        # Extract topics and their factors
        topics = data['TSC and Topics']['Topics']
        topic_factors = []

        # Collect all K and A factors present in topics
        extra_factors = set()
        for topic in topics:
            # Extract K and A factors from the topic (assuming it's in the form of 'K[number], A[number]')
            factors = re.findall(r'(K\d+|A\d+)', topic)
            topic_factors.append(set(factors))

            # Check for extra factors (those not in Knowledge or Ability)
            for factor in factors:
                if factor not in knowledge_factors and factor not in ability_factors:
                    extra_factors.add(factor)

        # Validate that each Knowledge and Ability factor is accounted for by at least one topic
        all_factors_accounted_for = True
        missing_factors = []

        # Check each Knowledge factor
        for k in knowledge_factors:
            if not any(k in topic for topic in topic_factors):
                missing_factors.append(f"Knowledge factor {k} is missing from topics")
                all_factors_accounted_for = False

        # Check each Ability factor
        for a in ability_factors:
            if not any(a in topic for topic in topic_factors):
                missing_factors.append(f"Ability factor {a} is missing from topics")
                all_factors_accounted_for = False

        # Handle extra factors (those not in Knowledge or Ability)
        if extra_factors:
            all_factors_accounted_for = False
            for extra in extra_factors:
                missing_factors.append(f"Extra factor {extra} found in topics but not in Knowledge or Ability list")

        # Print the custom error message if any factors are missing, else print success
        if not all_factors_accounted_for:
            error_message = "FAIL: " + "; ".join(missing_factors)
            print(error_message)
            sys.exit(error_message)  # Terminate the script with error code
        else:
            print("SUCCESS")

    except Exception as e:
        # Catch any unforeseen errors and print a custom error message before exiting
        print(f"ERROR: {str(e)}")
        sys.exit(error_message)
