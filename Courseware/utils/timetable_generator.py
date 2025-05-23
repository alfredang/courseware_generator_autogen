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
            You are AI assistant with expertise in generating structured timetable generator for WSQ courses based on the given context in JSON format {context}.
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
            #### 1. **Course Data & Completeness**
            - **Use all provided course details**, including Learning Units (LUs), topics, Learning Outcomes (LOs), Assessment Methods (AMs), and Instructional Methods (IMs).
            - **Always convert hours to minutes (e.g., 3.5 hrs = 210 mins) before allocating time.**
            - **For each Learning Unit, MANDATORY: Calculate and track the exact minutes allocated to topics and activities**
            - **For each Learning Unit, MANDATORY: Every Topic must have activities with the leftover time from LU_Duration after topics (e.g. Total LU_Duration= 210mins ,Total topic duration= 180 mins, Activity duration = LU_Duration - total topic duration = 210 mins- 180 mins = 30 mins)**
            - **You MUST maintain a running total of allocated minutes for each LU and ensure it EXACTLY matches the LU_Duration to the minute**
            - **Maximise every available minute: Do not leave any minute of LU_Duration unused. All time must be filled with either a topic or activity session.**
            - **Ensure Lu_Duration is fully utlised by each topic/activity. (e.g. "If LU1 Lu_Duration is 3.5 hours OR 210 minutes, ensure that the time given is fully utlised by both Topics and Activities")**
            - **If LU_Duration is not fully utilised, Teach the topic again and make sure to fully utilise the left over LU_Duration after the initial topics and activities**
            - **For the end of the course, MANDATORY: At the end of the course, Perform Course Feedback and TRAQOM Survey must happen before Final Assessment is conducted**
            - **MANDATORY: The sum of all session durations (including classroom and assessment) must EXACTLY match the course's total duration as specified in the input (Total_Course_Duration_Hours and Total_Course_Duration_Minutes).**
            - **Before generating the timetable, output a calculation table showing the duration of each session and the total. If the total does not match the course duration, adjust and recalculate until it matches exactly. Do not proceed until this check passes.**
            - **For each Topic or Activity, Ensure that they have their own references to their materials. (Example: Lecture ->Refer to some online references in Google Classroom LMS, Case study -> Refer to some online case studies in Google Classroom LMS)**
            
            **IMPORTANT!! Take note of the learning unit duration allocations or there will be errors when allocating the timetable!!! Make sure the timetable fulfills every point**
            #### 2. **Learning Unit Duration Allocation**
            - **Each Learning Unit (LU) has a specified LU_Duration (e.g., "3.5 hrs").**
            - **One Learning Unit (LU) might have one or multiple topics. Take note of the total number of topics, and split the LU_Duration accordingly**
            - **All Topic and Activity sessions within a LU must add up exactly to the LU_Duration. No minutes may be left unused.**
            - **Every minute of LU_Duration must be allocated to either a Topic or Activity session (never to breaks or non-instructional time).**
            - **Double-check that the sum of all Topic and Activity sessions for each LU matches the LU_Duration exactly.**
            - **For each Learning Unit, before generating the timetable, calculate and display:**
                - List the LU_Duration in minutes.
                - List each topic and activity with its assigned duration.
                - Show the sum of all topic and activity durations.
                - If the sum does not match LU_Duration, adjust and recalculate until it matches exactly.
                - Do not proceed to timetable generation until this check passes.
            -    For each Learning Unit, output a calculation table like:
                LU1: Catalysing HR with Generative AI (GAI)
                - LU_Duration: 210 mins
                - Topic 1: 180 mins
                - Activity: 30 mins
            -    Total allocated: 210 mins (must match LU_Duration)
            - **If the total allocated time does not match the LU_Duration, adjust the durations and recalculate until it matches. Do not proceed until this check passes.**
            
                            
            #### 3. **Breaks and Fixed Sessions**
            - **Lunch MUST be from 1200 to 1245**
            - **Lunch breaks, attendance sessions, and other breaks DO NOT count against LU_Duration.**
            - **LU_Duration only applies to the actual instruction and activity time.**
            - **When scheduling sessions, ensure breaks are inserted between LUs as needed without reducing the allocated LU_Duration.**
            
            #### 4. **Number of Days & Even Distribution**
            - Use **exactly {num_of_days}** day(s).
            - Distribute **topics, activities, and assessments** evenly across the day(s).
            - Ensure that each day has **exactly 9 hours** (0930hrs - 1830hrs), including breaks and assessments.
            - **Important:** The schedule for each day must start at the designated start time and end exactly at 1830hrs.

            ### **5. Instructional Methods & Resources**
            **Use ONLY these instructional methods** (extracted from the course context):  
            {list_of_im}
            DO NOT generate any IM pairs that are not in this list.
            Every session must have an instructional method pair that is in the list.
                    
            **Approved Resources:**
                - "Slide page #"
                - "TV"
                - "Whiteboard"
                - "Wi-Fi"
                - "Digital Attendance (PM)"
                - "Digital Attendance (Assessment)"

            ### **6. Fixed Sessions & Breaks**
            Each day must contain the following **fixed time slots**:

            #### **Day 1 First Timeslot (Mandatory)**
            - **Time:** "0930hrs - 0935hrs (5 mins)"
            - **Instructions:** 
            "Digital Attendance and Introduction to the Course"
                • Trainer Introduction
                • Learner Introduction
                • Overview of Course Structure
            - **Instructional_Methods:** "N/A"
            - **Resources:** "QR Attendance, Attendance Sheet"

            #### **Subsequent Days First Timeslot**
            - **Time:** "0930hrs - 0935hrs (5 mins)"
            - **Instructions:** "Digital Attendance (AM)"
            - **Instructional_Methods:** "N/A"
            - **Resources:** "QR Attendance, Attendance Sheet"

            #### **Mandatory Breaks**
            - **Lunch Break:** 45 mins
            - **Afternoon Break:** 5 mins

            #### **End-of-Day Recap (All Days Except Assessment Day)**
            - **Time:** "1825hrs - 1830hrs (5 mins)"
            - **Instructions:** "Recap All Contents and Close"
            - **Instructional_Methods:** [a valid Lecture or IM Pair from the context]
            - **Resources:** "Slide page #, TV, Whiteboard, Wi-Fi"

            ---

            ### **5. Final Day Assessments**
            - **Important! Make sure the final assessments are as follows below OR the timetable generated will be WRONG**
            - **On the last day of the course, the following sessions must be scheduled as the last timeslots of the day, in the exact order given below. No other sessions should follow these sessions.**
            - **The sessions are held after the all topics and activities are conducted.**
            - On the Assessment day, the following sessions must be scheduled as the **last timeslots** of the day, in the exact order given below. **No other sessions should follow these sessions.**

            1. **Final Course Feedback and TRAQOM Survey**
            - **Time:** "[Start Time] - [End Time] ([Duration])" (Duration must be 5 mins)
            - **Instructions:** "Course Feedback and TRAQOM Survey"
            - **Instructional_Methods:** "N/A"
            - **Resources:** "Feedback Forms, Survey Links"
            
            2. **Final Assessment Session(s)**
            - For each Assessment Method in the course details, schedule a Final Assessment session:
                - **Time:** "[Start Time] - [End Time] ([Duration])" (Duration must align with each assessment method's `Total_Delivery_Hours`.)
                - **Instructions:** "Final Assessment: [Assessment Method Full Name] ([Method Abbreviation])"
                - **Instructional_Methods:** "Assessment"
                - **Resources:** "Digital Attendance (Assessment), Assessment Questions, Assessment Plan"

            

            ---

            ### **6. Topic & Activity Session Structure**
            #### **Topic Sessions**
            - **Time:** Varies (e.g., "0945hrs - 1050hrs (65 mins)")
            - **Ensure the reference line is added to each topic or activity session.**
            - **Duration** If the topic is longer than 2 hours, split the session into half sessions with breaks in between depending on available time."
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
            ],
            "reference_line": "Refer to some online references in Google Classroom LMS,
            ```
            and
            ```json
            "instruction_title": "Topic 1: Interpretation of a Balance Sheet (A1) (Cont.)",
            "bullet_points": [
                "Understanding the various types of financial ratios that can be derived from the Balance Sheet"
            ],
            "reference_line": "Refer to some online references in Google Classroom LMS,
            ```
            
            Example Output for a single day:
            ```json
                        {{
                "lesson_plan": [
                {{
                    "Day": "Day 1",
                    "Sessions": [
                        {{
                            "Time": "0930hrs - 0935hrs (5 mins)",
                            "instruction_title": "Digital Attendance and Introduction to the Course",
                            "bullet_points": [
                                "Trainer Introduction",
                                "Learner Introduction",
                                "Overview of Course Structure"
                            ],
                            "Instructional_Methods": "N/A",
                            "Resources": "QR Attendance, Attendance Sheet"
                        }},
                        {{
                            "Time": "0935hrs - 1040hrs (65 mins)",
                            "instruction_title": "Topic 1: Introduction to Digital Humans (K1, A1)",
                            "bullet_points": [
                                "Definition and overview of digital humans",
                                "Key applications in branding and customer service"
                            ],
                            "reference_line": "Refer to some online references in Google Classroom LMS,
                            "Instructional_Methods": "Lecture, Group Discussion",
                            "Resources": "Slide page 1-5, TV, Whiteboard, Wi-Fi",
                        }},
                        {{
                            "Time": "1040hrs - 1140hrs (60 mins)",
                            "instruction_title": "Activity: Case Studies of Digital Human Applications (K2, A2)",
                            "bullet_points": [],
                            "reference_line": "Refer to some case studyies in Google Classroom LMS,
                            "Instructional_Methods": "Case Study",
                            "Resources": "N/A"
                        }},
                        {{
                            "Time": "1140hrs - 1200hrs (20 mins)",
                            "instruction_title": "Activity: Group Discussion on Case Studies",
                            "bullet_points": [],
                            "reference_line": "Refer to some online discussion in Google Classroom LMS,
                            "Instructional_Methods": "Group Discussion",
                            "Resources": "N/A"
                        }},
                        {{
                            "Time": "1200hrs - 1245hrs (45 mins)",
                            "instruction_title": "Lunch Break",
                            "bullet_points": [],
                            "Instructional_Methods": "N/A",
                            "Resources": "N/A"
                        }},
                        {{
                            "Time": "1245hrs - 1345hrs (60 mins)",
                            "instruction_title": "Topic 3: Designing Digital Human Interactions (K3, A3)",
                            "bullet_points": [
                                "Principles of effective digital human design",
                                "Tools and platforms overview"
                            ],
                            "reference_line": "Refer to some online references in Google Classroom LMS,
                            "Instructional_Methods": "Lecture, Demonstration",
                            "Resources": "Slide page 11-15, TV, Wi-Fi"
                        }},
                        {{
                            "Time": "1345hrs - 1350hrs (5 mins)",
                            "instruction_title": "Afternoon Break",
                            "bullet_points": [],
                            "Instructional_Methods": "N/A",
                            "Resources": "N/A"
                        }},
                        {{
                            "Time": "1350hrs - 1520hrs (90 mins)",
                            "instruction_title": "Topic 4: Hands-on Practice: Creating a Digital Human Scenario (A4)",
                            "bullet_points": [
                                "Step-by-step guide to building a digital human scenario",
                                "Peer feedback and sharing"
                            ],
                            "reference_line": "Refer to some online references in Google Classroom LMS,
                            "Instructional_Methods": "Demonstration, Practice",
                            "Resources": "Slide page 16-20, TV, Wi-Fi"
                        }},
                        {{
                            "Time": "1520hrs - 1825hrs (185 mins)",
                            "instruction_title": "Activity: Group Project Work",
                            "bullet_points": [],
                            "reference_line": "Refer to some online references in Google Classroom LMS,
                            "Instructional_Methods": "Practice, Group Discussion",
                            "Resources": "N/A"
                        }},
                        {{
                            "Time": "1825hrs - 1830hrs (5 mins)",
                            "instruction_title": "Recap All Contents and Close",
                            "bullet_points": [
                                "Summary of key learning points",
                                "Q&A"
                            ],
                            "Instructional_Methods": "Lecture, Group Discussion",
                            "Resources": "Slide page 21, TV, Whiteboard, Wi-Fi"
                        }}
                        // Additional sessions for the day
                    ]
                }},
                // Additional days
            ]
        }}
            ```

            #### **Activity Sessions**
            - **Duration:** Determined by the associated leftover time after the topic session.
            - **Must immediately follow the corresponding topic session.**
            - **Instructions Format:**  
            - **instruction_title:** e.g., "Activity: Demonstration on [Description]" or "Activity: Case Study on [Description]"
            - **bullet_points:** ["Bullet point 1", "Bullet point 2", "..."]

            #### **7. Adjustments on Topic Allocation**
            - **If there are too many topics to fit within {num_of_days} day(s):**
            - Adjust session durations while ensuring all topics and their bullet points are covered.
            - **If there are too few topics to fill all timeslots:**
            - You may split the bullet points of a topic across multiple sessions.
            - You may add one, and only one, **Recap All Contents and Close** session per day **(if needed for when there is extra time on the assessment day before the assessments)**, placed immediately before the Course Feedback and TRAQOM Survey Timeslot.  
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
                                "reference_line": "Refer to ... in Google Classroom LMS",
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
            
            ### **9. Google Classroom LMS Reference Line**
            For each session, add a new field called `"reference_line"` immediately after `"bullet_points"`.  
            Set its value depending on the instructional method(s) used:
            - **Lecture:** "Refer to some online references in Google Classroom LMS"
            - **Case Study:** "Refer to some online case studies in Google Classroom LMS"
            - **Peer Sharing / Group Discussion:** "Refer to some online discussion in Google Classroom LMS"
            - **Demonstration / Practice:** "Refer to some online practices in Google Classroom LMS"
            - **Role Play:** "Generate some roles depending on the LU"
            - **Activity sessions:** Use the line that matches the instructional method(s) for the activity.
            - If multiple instructional methods are present, include all relevant lines, separated by a semicolon.
            - Do **not** add a reference line for sessions where "Instructional_Methods" is "N/A" (e.g., breaks, attendance). In that case, omit the `"reference_line"` field.

            **Example:**
            ```json
            {{
                "instruction_title": "Topic 3: Designing Digital Human Interactions (K3, A3)",
                "bullet_points": [
                    "Principles of effective digital human design",
                    "Tools and platforms overview"
                ],
                "reference_line": "Refer to some online references in Google Classroom LMS,
                "Instructional_Methods": "Lecture, Demonstration",
                "Resources": "Slide page 11-15, TV, Wi-Fi"
            }}
            ```
            
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