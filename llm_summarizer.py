import openai
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class LLMSummarizer:
    def __init__(self, api_key: str):
        if not api_key or api_key == "YOUR_OPENAI_API_KEY":
            raise ValueError("OpenAI API key is not configured.")
        openai.api_key = api_key

    def _generate_text(self, prompt: str, max_tokens: int = 150) -> str:
        try:
            logger.info(f"Sending prompt to OpenAI: {prompt}")
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            generated_text = response.choices[0].text.strip()
            logger.info(f"Received from OpenAI: {generated_text}")
            return generated_text
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return "Could not generate summary."

    def generate_energy_summary(self, estimation_data: Dict) -> List[str]:
        summary_points = [
            "Predicted monthly energy costs using AI",
            "Based on weather, building data, and past usage",
            "Sustainability rating for this apartment compared to similar units"
        ]
        return summary_points

    def generate_safety_summary(self, safety_data: Dict) -> Dict:
        prompt = f"""
        Given the following safety analysis for a NYC neighborhood, generate a concise summary and a few key recommendations.
        
        Data:
        - Safety Score: {safety_data.get('score', 'N/A')} out of 5
        - Safety Grade: {safety_data.get('grade', 'N/A')}
        - Description: {safety_data.get('description', 'N/A')}
        - Total Complaints in Area: {safety_data.get('total_complaints', 'N/A')}
        
        Generate a human-readable "Area Summary" and 3-4 bulleted "Safety Recommendations".
        """
        
        generated_text = self._generate_text(prompt, max_tokens=200)

        # Basic parsing of the generated text
        summary = "Could not generate summary."
        recommendations = ["Could not generate recommendations."]

        if "Area Summary" in generated_text and "Safety Recommendations" in generated_text:
            parts = generated_text.split("Safety Recommendations")
            summary = parts[0].replace("Area Summary", "").strip()
            recommendations = [rec.strip() for rec in parts[1].strip().split('•') if rec.strip()]

        return {"summary": summary, "recommendations": recommendations} 