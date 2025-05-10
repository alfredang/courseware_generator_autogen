import json
import sys
import os

# Load the ensemble output JSON
with open('json_output/ensemble_output.json', 'r') as f:
    ensemble_output = json.load(f)

# Define our own version of the function for testing
def combine_los_and_topics_test(ensemble_output):
    """
    Combines all Learning Outcomes (LOs) and Topics from the ensemble_output into a formatted string
    with Learning Outcomes section followed by Course Outline section organized by Learning Units.
    """

    # Start with Learning Outcomes header
    result = "Learning Outcomes\n"
    
    # Extract Learning Outcomes
    learning_outcomes = ensemble_output["Learning Outcomes"]["Learning Outcomes"]
    result += "\n".join(learning_outcomes) + "\n\n"
    
    # Add Course Outline header
    result += "Course Outline:\n"
    
    # Extract Learning Units
    learning_units = ensemble_output["TSC and Topics"].get("Learning Units", [])
    
    # Get the topics for each Learning Unit from the Course Outline
    course_outline = ensemble_output["Assessment Methods"]["Course Outline"]["Learning Units"]
    
    # Process each Learning Unit
    for lu_index, lu_title in enumerate(learning_units):
        lu_num = f"LU{lu_index + 1}"
        
        # Extract the title after "LUx: "
        lu_title_clean = lu_title.split(": ", 1)[1] if ": " in lu_title else lu_title
        # Remove any KA references in parentheses
        lu_title_clean = lu_title_clean.split(" (")[0] if " (" in lu_title_clean else lu_title_clean
        
        # Add the Learning Unit header
        result += f"{lu_num}: {lu_title_clean} \n"
        result += "Topics:\n"
        
        # Get topics for this Learning Unit
        if lu_num in course_outline:
            topics = course_outline[lu_num].get("Description", [])
            
            for topic in topics:
                topic_title = topic.get("Topic", "")
                
                # Extract topic number (e.g., "Topic 1" -> "T1")
                topic_num = topic_title.split("Topic ")[1].split(":")[0] if "Topic " in topic_title else ""
                
                # Extract topic name without the KA references
                topic_name = topic_title.split(': ', 1)[1] if ": " in topic_title else topic_title
                topic_name = topic_name.split(' (')[0] if " (" in topic_name else topic_name
                
                # Add the topic
                result += f"•\tT{topic_num}: {topic_name} \n"
        
        result += "\n"
    
    return result

# Call the function
result = combine_los_and_topics_test(ensemble_output)

# Print the result
print(result) 