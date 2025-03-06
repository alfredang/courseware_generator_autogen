from pydantic import BaseModel, Field
from typing import List

class KnowledgeStatement(BaseModel):
    id: str
    text: str


class AbilityStatement(BaseModel):
    id: str
    text: str


class Topic(BaseModel):
    name: str
    subtopics: List[str]
    tsc_knowledges: List[KnowledgeStatement]
    tsc_abilities: List[AbilityStatement]


class LearningUnit(BaseModel):
    name: str
    topics: List[Topic]
    learning_outcome: str


class AssessmentMethod(BaseModel):
    code: str
    duration: str
    
class FacilitatorGuideExtraction(BaseModel):
    course_title: str
    tsc_proficiency_level: str
    learning_units: List[LearningUnit]
    assessments: List[AssessmentMethod]

class CaseStudyQuestion(BaseModel):
    question: str
    answer: str
    ability_id: List[str]

class CaseStudy(BaseModel):
    scenario: str
    questions: List[CaseStudyQuestion]

# Define the WSQ model for structured output
class WSQ(BaseModel):
    knowledge_id: str = Field(..., description="The ID of the Knowledge Statement, e.g., K1, K2.")
    knowledge_statement: str = Field(..., description="The text of the Knowledge Statement.")
    scenario: str = Field(..., description="The realistic workplace scenario.")
    question: str = Field(..., description="The question based on the scenario.")
    answer: str = Field(..., description="The concise answer to the question.")

class LearningOutcomeContent(BaseModel):
    ability_id: List[str]
    retrieved_content: str = Field(..., description="The content retrieved for this Knowledge Statement.")