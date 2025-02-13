# timetable_generator.py

import re
import json
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage

def extract_unique_instructional_methods(course_context):
    unique_methods = set()

    # Define valid instructional method pairs (including "Role Play")
    valid_im_pairs = {
        ("Lecture", "Didactic Questioning"),
        ("Lecture", "Peer Sharing"),
        ("Lecture", "Group Discussion"),
        ("Demonstration", "Practice"),
        ("Demonstration", "Group Discussion"),
        ("Case Study",),
        ("Role Play",)  # Role Play is a standalone method
    }

    for lu in course_context.get("Learning_Units", []):
        extracted_methods = lu.get("Instructional_Methods", [])

        # Fix replacements BEFORE grouping
        corrected_methods = []
        for method in extracted_methods:
            if method == "Classroom":
                corrected_methods.append("Lecture")
            elif method == "Practical":
                corrected_methods.append("Practice")
            elif method == "Discussion":
                corrected_methods.append("Group Discussion")
            else:
                corrected_methods.append(method)

        # Generate valid IM pairs from the extracted methods
        method_pairs = set()
        for pair in valid_im_pairs:
            if all(method in corrected_methods for method in pair):
                method_pairs.add(", ".join(pair))  # Convert tuple to a string

        # If no valid pairs were found, create custom pairings
        if not method_pairs and corrected_methods:
            if len(corrected_methods) == 1:
                method_pairs.add(corrected_methods[0])  # Single method as standalone
            elif len(corrected_methods) == 2:
                method_pairs.add(", ".join(corrected_methods))  # Pair both together
            else:
                # Pair first two and last two methods together
                method_pairs.add(", ".join(corrected_methods[:2]))
                if len(corrected_methods) > 2:
                    method_pairs.add(", ".join(corrected_methods[-2:]))

        # Update the unique set
        unique_methods.update(method_pairs)

    return unique_methods


async def generate_timetable(context, num_of_days, model_client):

    list_of_im = extract_unique_instructional_methods(context)

    timetable_generator_agent = AssistantAgent(
        name="Timetable_Generator",
        model_client=model_client,
        system_message=f"""
        You are a timetable generator for WSQ courses.
        Your task is to create a **detailed and structured lesson plan timetable** for a WSQ course based on the provided course information and context. **Every generated timetable must strictly follow the rules below to maintain quality and accuracy.**

        ---

        ### **Instructions:**
        #### 1. **Course Data & Completeness**
        - **Use all provided course details**, including Learning Units (LUs), topics, Learning Outcomes (LOs), Assessment Methods (AMs), and Instructional Methods (IMs).
        - **Do not omit any topics or bullet points.**  
        - **Ensure that every topic is included and each bullet point is addressed in at least one session.**
        
        #### 2. **Number of Days & Even Distribution**
        - Use **exactly {num_of_days}** day(s).
        - Distribute **topics, activities, and assessments** evenly across the day(s).
        - Ensure that each day has **exactly 9 hours** (0930hrs - 1830hrs), including breaks and assessments.

        ### **3. Instructional Methods & Resources**

        **Use ONLY these instructional methods** (extracted from the course context):  
        {list_of_im}
        DO NOT generate any IM pairs that are not in this list.

        Every session must have an instructional method pair that is in the list.
                
        **Approved Resources:**
            - "Slide page #"
            - "TV"
            - "Whiteboard"
            - "Wi-Fi"

        ### **4. Fixed Sessions & Breaks**
        Each day must contain the following **fixed time slots**:

        #### **Day 1 First Timeslot (Mandatory)**
        - **Time:** "0930hrs - 0945hrs (15 mins)"
        - **Instructions:** 
        "Digital Attendance and Introduction to the Course"
            • Trainer Introduction
            • Learner Introduction
            • Overview of Course Structure
        - **Instructional_Methods:** "N/A"
        - **Resources:** "QR Attendance, Attendance Sheet" ## TV, Laptop, Wi-Fi if applicable based on course

        #### **Subsequent Days First Timeslot**
        - **Time:** "0930hrs - 0940hrs (10 mins)"
        - **Instructions:** "Digital Attendance (AM)"
        - **Instructional_Methods:** "N/A"
        - **Resources:** "QR Attendance, Attendance Sheet" ## TV, Laptop, Wi-Fi if applicable based on course

        #### **Mandatory Breaks**
        - **Morning Break:**  "1050hrs - 1100hrs (10 mins)"  
        - **Lunch Break:**  "1200hrs - 1245hrs (45 mins)"  
        - **Digital Attendance (PM):**  "1330hrs - 1340hrs (10 mins)"  
        - **Afternoon Break:**  "1500hrs - 1510hrs (10 mins)"  

        #### **End-of-Day Recap (All Days Except Assessment Day)**
        - **Time:** "1810hrs - 1830hrs (20 mins)"
        - **Instructions:** "Recap All Contents and Close"
        - **Instructional_Methods:** [a valid Lecture,... IM Pair in the list of IM pair from context] // Adhere to the rules in 4.
        - **Resources:** "Slide page #, TV, Whiteboard"

        ---

        ### **5. Final Day Assessments**
        Assessments must follow these strict scheduling rules:

        #### **Pre-assessment Digital Attendance (10 mins) is required.**
        - **Time:** "[Start Time] - [End Time] (10 mins)"
        - **Instructions:** "Digital Attendance (Assessment)"
        - **Instructional_Methods:** "N/A"
        - **Resources:** "QR Attendance, Attendance Sheet" ## TV, Laptop, Wi-Fi if applicable based on course

        #### **Final Assessments Sessions**
        For Each Assessment Method:
        - **Time:** "[Start Time] - [End Time] ([Duration])"
        - **Instructions:** "Final Assessment: [Assessment Method Full Name] ([Method Abbreviation])"
        - **Instructional_Methods:** "Assessment"
        - **Resources:** "Assessment Questions, Assessment Plan"

        #### **Final Course Feedback Session**
        - **Time:** "1810hrs - 1830hrs (20 mins)" // Fixed Timeslot and Duration
        - **Instructions:** "Course Feedback and TRAQOM Survey"
        - **Instructional_Methods:** "N/A"
        - **Resources:** "Feedback Forms, Survey Links"

        - Duration of final assessment sessions to align with each assessment method `Total_Delivery_Hours` in context `Assessment_Methods_Details` 
        - **No gaps or overlaps** between assessment slots.
        
        ---

        ### **6. Topic & Activity Session Structure**
        #### **Topic Sessions**
        - **Time:** Varies (e.g., "0945hrs - 1050hrs (65 mins)")
        - **Instructions Format:**  

        **Topic X: [Topic Title] (K#, A#)**
        
        • [Bullet Point 1]
        • [Bullet Point 2]

        - All topics must have at least one session.
        - No bullet points should be left out.
        - Session durations range from 30 to 120 minutes.
        
        **Activity Sessions**
        - Duration: Fixed at 10 minutes.
        - Must immediately follow the corresponding topic session.
        
        - Instruction format:
            For "Demonstration, Practice" or "Demonstration, Group Discussion":
            Activity: Demonstration on [Description]
        
            For "Case Study":
            Activity: Case Study on [Description]

        #### 7. **Adjustments on Topic Allocation*
        To ensure that all timeslots are fully utilized, apply the following adjustments based on the number of topics available:

        **If there are too many topics to fit within {num_of_days} day(s)**:
        - Adjust session durations while ensuring all topics and bullet points are covered.
        - Increase the number of bullet points covered per session to optimize learning time.
        - Combine similar bullet points within a session where appropriate, but do not omit any.
        
        **If there are too few topics to fill all timeslots**:
        - Reuse bullet points across multiple timeslots to reinforce learning, but the sequence must be logical.
        - Alternatively, extend the duration of Topic sessions to allocate more time for learning. 
        - You are still required to strictly adhere to the instructions format from Instruction 4 or 6:
        **Instructions:**: 
            **Topic X: [Topic Title] (K#, A#)**
            
            • [Bullet Point 1]
            • [Bullet Point 2]
        - Can allocate ONE recap session right before the Pre-Assessment Attendance Timeslot.
        **Time:** "[Start Time] - [End Time] ([Duration])" (Maximum Duration of STRICTLY 60 mins) 
        **Instructions:** "Recap All Contents and Close"

        ---

        ### **8. Output Format**
        The output must strictly follow this JSON structure:

        ```json
        {{
            "lesson_plan": [
                {{
                    "Day": "Day X",
                    "Sessions": [
                        {{
                            "Time": "Start - End (duration)",
                            "Instructions": "Session content",
                            "Instructional_Methods": "Method pair",
                            "Resources": "Required resources"
                        }},
                        // Additional sessions for the day
                    ]
                }},
                // Additional days
            ]
        }}
        ```
        All timings must be consecutive without gaps or overlaps.
        The total number of days in the timetable must match {num_of_days}.
    """
    )

    agent_task = f"""
        1. Take the complete dictionary provided:
        {context}
        2. Use the provided JSON dictionary, which includes all the course information, to generate the lesson plan timetable.

        **Instructions:**
        1. Adhere to all the rules and guidelines.
        2. Include the timetable data under the key 'lesson_plan' within a JSON dictionary.
        3. Return the JSON dictionary containing the 'lesson_plan' key.
    """

    # Process sample input
    response = await timetable_generator_agent.on_messages(
        [TextMessage(content=agent_task, source="user")], CancellationToken()
    )

    try:
        timetable_response = json.loads(response.chat_message.content)
        if 'lesson_plan' not in timetable_response:
            raise Exception("No lesson_plan key found in timetable data")
        return timetable_response

    except Exception as e:
        raise Exception(f"Failed to parse timetable JSON: {str(e)}")
