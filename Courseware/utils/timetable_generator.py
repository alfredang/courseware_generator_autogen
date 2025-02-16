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
            - **Important:** The schedule for each day must start at the designated start time and end exactly at 1830hrs.

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
            - **Resources:** "QR Attendance, Attendance Sheet"

            #### **Subsequent Days First Timeslot**
            - **Time:** "0930hrs - 0940hrs (10 mins)"
            - **Instructions:** "Digital Attendance (AM)"
            - **Instructional_Methods:** "N/A"
            - **Resources:** "QR Attendance, Attendance Sheet"

            #### **Mandatory Breaks**
            - **Morning Break:**  "1050hrs - 1100hrs (10 mins)"  
            - **Lunch Break:**  "1200hrs - 1245hrs (45 mins)"  
            - **Digital Attendance (PM):**  "1330hrs - 1340hrs (10 mins)"  
            - **Afternoon Break:**  "1500hrs - 1510hrs (10 mins)"  

            #### **End-of-Day Recap (All Days Except Assessment Day)**
            - **Time:** "1810hrs - 1830hrs (20 mins)"
            - **Instructions:** "Recap All Contents and Close"
            - **Instructional_Methods:** [a valid Lecture or IM Pair from the context]
            - **Resources:** "Slide page #, TV, Whiteboard"

            ---

            ### **5. Final Day Assessments**
            On the Assessment day, the following sessions must be scheduled as the **last timeslots** of the day, in the exact order given below. **No other sessions should follow these sessions.**

            1. **Digital Attendance (Assessment) (10 mins)**
            - **Time:** "[Start Time] - [End Time] (10 mins)"
            - **Instructions:** "Digital Attendance (Assessment)"
            - **Instructional_Methods:** "N/A"
            - **Resources:** "QR Attendance, Attendance Sheet"

            2. **Final Assessment Session(s)**
            - For each Assessment Method in the course details, schedule a Final Assessment session:
                - **Time:** "[Start Time] - [End Time] ([Duration])" (Duration must align with each assessment method's `Total_Delivery_Hours`.)
                - **Instructions:** "Final Assessment: [Assessment Method Full Name] ([Method Abbreviation])"
                - **Instructional_Methods:** "Assessment"
                - **Resources:** "Assessment Questions, Assessment Plan"

            3. **Final Course Feedback and TRAQOM Survey**
            - **Time:** "1810hrs - 1830hrs (20 mins)"
            - **Instructions:** "Course Feedback and TRAQOM Survey"
            - **Instructional_Methods:** "N/A"
            - **Resources:** "Feedback Forms, Survey Links"

            ---

            ### **6. Topic & Activity Session Structure**
            #### **Topic Sessions**
            - **Time:** Varies (e.g., "0945hrs - 1050hrs (65 mins)")
            - **Instructions Format:**  
            Instead of a single string, break the session instructions into:
            - **instruction_title:** e.g., "Topic X: [Topic Title] (K#, A#)"
            - **bullet_points:** A list containing each bullet point for the topic.
            
            **Important:** If there are too few topics to fill the schedule, you are allowed to split the bullet points of a single topic across multiple sessions. In that case, each session should cover a different subset of bullet points, and together they must cover all bullet points for that topic.
          
            Example:
            ```json
            "instruction_title": "Topic 1: Interpretation of a Balance Sheet (A1)",
            "bullet_points": [
                "Understanding the different components of a Balance Sheet and where to find value of any business in any Balance Sheet."
            ]
            ```
            and
            ```json
            "instruction_title": "Topic 1: Interpretation of a Balance Sheet (A1) (Cont.)",
            "bullet_points": [
                "Understanding the various types of financial ratios that can be derived from the Balance Sheet"
            ]
            ```

            #### **Activity Sessions**
            - **Duration:** Fixed at 10 minutes.
            - **Must immediately follow the corresponding topic session.**
            - **Instructions Format:**  
            - **instruction_title:** e.g., "Activity: Demonstration on [Description]" or "Activity: Case Study on [Description]"
            - **bullet_points:** **This must be an empty list.**
                **Note:** Activity timeslots must strictly have no bullet points.

            #### **7. Adjustments on Topic Allocation**
            - **If there are too many topics to fit within {num_of_days} day(s):**
            - Adjust session durations while ensuring all topics and their bullet points are covered.
            - **If there are too few topics to fill all timeslots:**
            - You may split the bullet points of a topic across multiple sessions.
            - You may add one, and only one, **Recap All Contents and Close** session per day **(if needed)**, placed immediately before the Digital Attendance (Assessment) Timeslot.  
            **Do not generate multiple Recap sessions.**
            - This Recap session is a fallback option only when there are insufficient topic sessions; it should not replace the bullet point details of the topic sessions.

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
                                "instruction_title": "Session title (e.g., Topic 1: ... or Activity: ...)",
                                "bullet_points": ["Bullet point 1", "Bullet point 2", "..."],
                                "Instructional_Methods": "Method pair",
                                "Resources": "Required resources"
                            }}
                            // Additional sessions for the day
                        ]
                    }}
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