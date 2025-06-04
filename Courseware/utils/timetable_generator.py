"""
File: timetable_generator.py

===============================================================================
Timetable Generator Module
===============================================================================
Description:
    This module generates a structured lesson plan timetable based on the provided course context.
    It leverages an AI assistant agent to produce a detailed and balanced lesson plan that adheres
    strictly to WSQ course structure rules. The generated timetable ensures even distribution of topics,
    fixed sessions (such as attendance, breaks, and final assessments), and appropriate use of instructional
    methods over the specified number of days.

Main Functionalities:
    • extract_unique_instructional_methods(course_context):
          Extracts and processes unique instructional method combinations from each Learning Unit in the
          course context by correcting method names and grouping them into valid pairs.
    • generate_timetable(context, num_of_days, model_client):
          Uses an AI assistant agent to generate a complete lesson plan timetable in JSON format.
          The timetable includes fixed sessions (attendance, breaks, assessment sessions) and topic or
          activity sessions, distributed evenly across the specified number of days.

Dependencies:
    - autogen_agentchat.agents (AssistantAgent)
    - autogen_core (CancellationToken)
    - autogen_agentchat.messages (TextMessage)
    - utils.helper (parse_json_content)
    - Standard Python Libraries (built-in)

Usage:
    - Ensure the course context includes complete details such as Learning Units, Topics, Learning Outcomes,
      Assessment Methods, and Instructional Methods.
    - Configure an AI model client and specify the number of days (num_of_days) for the timetable.
    - Call generate_timetable(context, num_of_days, model_client) to generate the lesson plan timetable.
    - The function returns a JSON dictionary with the key "lesson_plan", containing a list of daily session
      schedules formatted according to WSQ rules.

Author:
    Derrick Lim
Date:
    3 March 2025
===============================================================================
"""

from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
from utils.helper import parse_json_content

def extract_unique_instructional_methods(course_context):
    """
    Extracts and processes unique instructional method combinations from the provided course context.

    This function retrieves instructional methods from each Learning Unit (LU) in the course context,
    applies corrections for known replacements, and groups them into predefined valid instructional method
    pairs. If no predefined pairs exist, it generates custom pairings.

    Args:
        course_context (dict):
            A dictionary containing course details, including a list of Learning Units with instructional methods.

    Returns:
        set:
            A set of unique instructional method combinations, formatted as strings.

    Raises:
        KeyError:
            If "Learning_Units" is missing or incorrectly formatted in the course context.
    """

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
    """
    Generates a structured lesson plan timetable based on the provided course context.

    This function uses an AI assistant agent to create a timetable that adheres to WSQ course structure rules.
    It ensures balanced topic distribution across the specified number of days, maintains session timing integrity,
    and applies predefined instructional methods.

    Args:
        context (dict): 
            A dictionary containing course details, including Learning Units, Learning Outcomes, 
            and Assessment Methods.
        num_of_days (int): 
            The number of days over which the course timetable should be distributed.
        model_client: 
            An AI model client instance used to generate the lesson plan.

    Returns:
        dict: 
            A dictionary containing the generated lesson plan under the key `"lesson_plan"`, 
            structured as a list of sessions for each day.

    Raises:
        Exception:
            If the generated timetable response is missing the required `"lesson_plan"` key or 
            fails to parse correctly.
    """
    
    list_of_im = extract_unique_instructional_methods(context)

    timetable_generator_agent = AssistantAgent(
        name="Timetable_Generator",
        model_client=model_client,
        system_message=f"""
            You are AI assistant with expertise in generating structured timetable generator for WSQ courses based on the given context in JSON format {{context}}.
            Understand the course context and generate a detailed lesson plan timetable that adheres to the WSQ course structure rules. Make sure to follow the instructions carefully.
            The course context includes the following details which you should use to generate the timetable. Pay special attention to the LU_Duration provided in the course context to ensure the timetable is accurate:
            - Course_Title
            - TSC_Code
            - Total_Course_Duration_Hours
            - Total_Course_Duration_Minutes
            - Total_Training_Hours
            - Total_Assessment_Hours
            - LU_Title (LUs)
            - Learning_Unit_Duration (LU_Duration)
            - Topics
            - Topic_Title
            - Bullet_Points
            - Learning Outcomes (LOs)
            - Assessment Methods (AMs)
            - Instructional Methods (IMs)
            
            Your task is to create a **detailed and structured lesson plan timetable** for a WSQ course based on the provided course information and context. **Every generated timetable must strictly follow the rules below to maintain quality and accuracy.**
            
            ---
            **IMPORTANT! Ensure the rules are followed closely or the time table generated will be inaccurate.**
            ### **Instructions:**

            #### 1. **Overall Structure & Duration**
            - Use all provided course details: LUs, topics, LOs, AMs, IMs.
            - **LU Duration Adherence:** The sum of durations for all Topic and Activity sessions within a Learning Unit (LU) MUST EXACTLY match that LU's specified `LU_Duration`. Convert all `LU_Duration` (e.g., "3.5 hrs") to minutes for allocation and ensure every minute is used.
            - **Topic/Activity Allocation:** If an LU is "3.5 hours" (210 minutes), you might allocate it as: Topic (2 hours = 120 mins), same Topic continued (1 hour = 60 mins), Activity (30 mins). Or Topic (3 hours = 180 mins), Activity (30 mins).
            - **Session Durations:** All session durations (for topics, activities, breaks, assessments) MUST be in multiples of 15 minutes (e.g., 15min, 30min, 45min, 1hr, 1hr 15min, 2hr 30min).
            - **Total Course Duration:** The sum of all session durations across all days (including topics, activities, breaks, and assessments) must EXACTLY match the course's total duration.
            - **No Fixed Daily End Time:** Days conclude when the planned LUs/topics for that day are completed, respecting LU duration rules. There's no strict 1830hrs cutoff unless it coincides with content completion.
            - **Reference Line:** For every Topic session, include a `reference_line` field with the value "Refer to online references in Google Classroom LMS". For Activity sessions, the `reference_line` should correspond to its Instructional Method (e.g., "Refer to some online case studies in Google Classroom LMS" for Case Study). Omit `reference_line` or set to empty string if Instructional_Methods is "N/A".

            #### 2. **Fixed Sessions and Formatting**

            ##### **Digital Attendance:**
            - **Day 1 - First Session (Mandatory):**
                - `starttime`: "0930", `endtime`: "0945", `duration`: "15min"
                - `instruction_title`: "Digital Attendance and Introduction to the Course"
                - `bullet_points`: ["Trainer Introduction", "Learner Introduction", "Overview of Course Structure"]
                - `Instructional_Methods`: "N/A"
                - `Resources`: "QR Attendance, Attendance Sheet"
                - `reference_line`: ""
            - **Subsequent Days - AM Attendance:**
                - The first *Topic session* of the day should incorporate AM attendance.
                - `instruction_title` should be like: "Digital Attendance (AM) & Topic X: [Topic Title] (K#, A#)"
                - `Resources` for this session must include "QR Attendance, Attendance Sheet" in addition to topic-specific resources. The duration of this session is primarily for the topic.
            - **PM Attendance (After Lunch):**
                - The first *Topic session* immediately following Lunch Break should incorporate PM attendance.
                - `instruction_title` should be like: "Digital Attendance (PM) & Topic Y: [Topic Title] (K#, A#)"
                - `Resources` for this session must include "Digital Attendance (PM)" in addition to topic-specific resources.

            ##### **Breaks:**
            - **Lunch Break:**
                - `duration`: "45min"
                - Timing: Flexible, can be scheduled between 11:30 and 13:00.
                - `instruction_title`: "Lunch Break"
                - `bullet_points`: []
                - `Instructional_Methods`: "N/A"
                - `Resources`: "N/A"
                - `reference_line`: ""
            - **Tea Break:**
                - `duration`: "10min"
                - Timing: Must be scheduled in the afternoon (after Lunch Break).
                - `instruction_title`: "Tea Break"
                - `bullet_points`: []
                - `Instructional_Methods`: "N/A"
                - `Resources`: "Refreshments"
                - `reference_line`: ""

            #### 3. **Instructional Methods & Resources**
            - **Topic Instructional Methods:** Primarily use combinations like "Lecture, Group Discussion", "Lecture, Peer Sharing". Use from the provided `list_of_im`: {{list_of_im}}
            - **Activity Instructional Methods:** Activities must use methods like "Case Study", "Demonstration", "Practice", "Role Play". **DO NOT use "Lecture", "Group Discussion", or "Peer Sharing" for activities.**
            - **Approved Resources (General):** "Slide page #", "TV", "Whiteboard", "Wi-Fi", "LMS". Specific attendance resources mentioned above.
            
            #### 4. **Topic and Activity Session Structure**
            - **Topic Sessions:**
                - `instruction_title`: "Topic X: [Topic Title] (K#, A#)" or "Topic X: [Topic Title] (continued) (K#, A#)" if a topic is split.
                - `bullet_points`: List of strings covering the content for that specific session.
                - `reference_line`: "Refer to online references in Google Classroom LMS"
            - **Activity Sessions:**
                - `instruction_title`: "Activity: [Descriptive Activity Name, e.g., Case studies on Identify Conflicts]"
                - `bullet_points`: Relevant bullet points for the activity, if any (can be an empty list).
                - `reference_line`: Based on IM (e.g., "Refer to some online case studies in Google Classroom LMS" for Case Study).
            - **Splitting Topics:** If a topic is long, its bullet points can be split across multiple consecutive sessions. Ensure the `instruction_title` reflects continuation (e.g., "Topic 1 (continued)").

            #### 5. **Final Day & Assessments**
            - **Course Feedback and TRAQOM Survey:**
                - This MUST be merged with the *last Activity session* on the assessment day, scheduled immediately before the Final Assessment(s).
                - The `instruction_title` for this activity session should be: "Activity: [Activity Name] & Course Feedback/TRAQOM Survey"
                - `Resources` for this session must include "LMS, Feedback Forms, Survey Links" in addition to activity-specific resources.
            - **Final Assessment Session(s):**
                - Scheduled as the absolute last sessions of the course, after the combined activity/feedback session.
                - For each Assessment Method from the course context:
                    - `instruction_title`: "Final Assessment: [Assessment Method Full Name]" (e.g., "Final Assessment: Written Assessment - Short Answer Questions")
                    - `duration`: Must align with the `Total_Delivery_Hours` for that specific assessment method, converted to a 15-min interval string.
                    - `Instructional_Methods`: "Assessment"
                    - `Resources`: "Digital Attendance Assessment, Assessment Plan" (First assessment may also include "Assessment Questions").
                    - `reference_line`: ""
            - **No Recap Sessions:** Do not include "Recap All Contents and Close" sessions.

            #### 6. **Number of Days**
            - Distribute content over **exactly {{num_of_days}}** day(s).

            ---
            ### **7. Output JSON Format**
            The output MUST be a JSON object with a single key "lesson_plan". The value is a list of days. Each day is an object with "Day" (e.g., "Day 1") and "Sessions". "Sessions" is a list of session objects.
            **Each session object MUST have the following structure and keys:**
            ```json
            {{
                "starttime": "HHMM",       // e.g., "0930", "1300"
                "endtime": "HHMM",         // e.g., "0945", "1430"
                "duration": "Xh Ymin",     // e.g., "15min", "1hr", "2hr 30min"
                "instruction_title": "String",
                "bullet_points": ["String list"], // Can be empty list []
                "Instructional_Methods": "String", // e.g., "Lecture, Group Discussion", "Case Study", "N/A"
                "Resources": "String",
                "reference_line": "String" // Optional, can be empty ""
            }}
            ```

            **Example Snippet for a Day:**
            ```json
                        {{
                "lesson_plan": [
                {{
                    "Day": "Day 1",
                    "Sessions": [
                        {{
                                "starttime": "0930",
                                "endtime": "0945",
                                "duration": "15min",
                            "instruction_title": "Digital Attendance and Introduction to the Course",
                                "bullet_points": ["Trainer Introduction", "Learner Introduction", "Overview of Course Structure"],
                            "Instructional_Methods": "N/A",
                                "Resources": "QR Attendance, Attendance Sheet",
                                "reference_line": ""
                        }},
                        {{
                                "starttime": "0945",
                                "endtime": "1145",
                                "duration": "2hr",
                                "instruction_title": "Digital Attendance (AM) & Topic 1: Identify Conflicts (K1, A1, A6)",
                                "bullet_points": ["Assess conflict situation", "Causes of conflict (K1)"],
                                "Instructional_Methods": "Lecture, Group Discussion, Peer Sharing",
                                "Resources": "QR Attendance, Attendance Sheet, Slide page 1-5, TV, Whiteboard, Wi-Fi, LMS",
                                "reference_line": "Refer to online references in Google Classroom LMS"
                        }},
                        {{
                                "starttime": "1145",
                                "endtime": "1230",
                                "duration": "45min",
                            "instruction_title": "Lunch Break",
                            "bullet_points": [],
                            "Instructional_Methods": "N/A",
                                "Resources": "N/A",
                                "reference_line": ""
                        }},
                        {{
                                "starttime": "1230",
                                "endtime": "1330",
                                "duration": "1hr",
                                "instruction_title": "Digital Attendance (PM) & Topic 1: Identify Conflicts (continued)",
                                "bullet_points": ["Determine ways to validate information and history of conflict (A1)", "Identify the possible causes of conflict (A1)", "Recognise factors and early indicators that give rise to conflicts (A6)"],
                                "Instructional_Methods": "Lecture, Group Discussion, Peer Sharing",
                                "Resources": "Digital Attendance (PM), Slide page 1-5, TV, Whiteboard, Wi-Fi, LMS",
                                "reference_line": "Refer to online references in Google Classroom LMS"
                            }},
                            {{
                                "starttime": "1330",
                                "endtime": "1400",
                                "duration": "30min",
                                "instruction_title": "Activity: Case studies on Identify Conflicts",
                                "bullet_points": [],
                                "Instructional_Methods": "Case Study",
                                "Resources": "LMS",
                                "reference_line": "Refer to some online case studies in Google Classroom LMS"
                            }}
                            // ... more sessions ...
                        ]
                    }}
                    // ... more days ...
                ]
            }}
            ```
            Ensure all timings are consecutive and logical. Calculate `endtime` based on `starttime` and `duration`.
            Adhere strictly to the 15-minute multiple rule for all `duration` fields.
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
        timetable_response = parse_json_content(response.chat_message.content)
        if 'lesson_plan' not in timetable_response:
            raise Exception("No lesson_plan key found in timetable data")
        return timetable_response

    except Exception as e:
        raise Exception(f"Failed to parse timetable JSON: {str(e)}")