"""
AI Intelligence Service for Yieldera Visualization
Generates professional commentary from geospatial statistics
"""

import logging
import requests
from typing import Dict, Optional
from ..config import settings

class AIIntelligence:
    """Service to generate AI-driven insights from GIS data"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.logger = logging.getLogger(__name__)
        
    def generate_commentary(self, statistics: Dict, region_name: str, analysis_type: str) -> str:
        """Generates executive summary using OpenAI with enhanced statistics"""
        
        if not self.api_key:
            return "AI Commentary unavailable (API Key not set). Please provide an OpenAI API Key."
            
        try:
            # Prepare the prompt with enriched data
            percentage_total = statistics.get('percentage_change', 0)
            mean_ndvi = statistics.get('mean_ndvi', 0)
            ndvi_change = statistics.get('ndvi_change', 0)
            
            cur_rain = statistics.get('mean_rainfall', 0)
            bas_rain = statistics.get('baseline_rainfall', 0)
            rain_change = statistics.get('rainfall_change', 0)
            
            zonal_impact = statistics.get('zonal_impact', {})
            multi_peril_risk = statistics.get('multi_peril_risk_hectares', 0)
            
            period_start = statistics.get('analysis_period', {}).get('start', 'Specified Period')
            period_end = statistics.get('analysis_period', {}).get('end', '')
            baseline_desc = statistics.get('baseline_period', 'Historical Baseline')
            
            # Build a string describing the impact for the prompt
            impact_context = ""
            for zone, data in zonal_impact.items():
                if data.get('area_ha', 0) > 1: # Only include significant areas
                    impact_context += (f"- {zone}: {data['area_ha']:,.0f} ha. "
                                     f"Moisture: {data['current_moisture']:.4f} (vs {data['baseline_moisture']:.4f} Hist). "
                                     f"Rain: {data['current_rain']:.2f}mm (vs {data['baseline_rain']:.2f}mm Hist)\n")

            prompt = f"""
            Task: Provide a high-impact EXECUTIVE SUMMARY for an Agricultural Risk Report.
            Target Audience: Decisive Executives (Prioritize percentage deviations over raw scientific decimals).
            Approach: COMPARATIVE (Current Season vs Historical Reference)
            
            REGION: {region_name}
            SATELLITE PERIOD: {period_start} to {period_end}
            REFERENCE PERIOD: {baseline_desc}
            
            CORE COMPARATIVE DATA:
            - SOIL MOISTURE: {percentage_total:+.1f}% Deviation from Historical ({statistics.get('current_mean', 0):.4f} Season vs {statistics.get('baseline_mean', 0):.4f} Baseline)
            - PRECIPITATION: {rain_change:+.1f}% Deviation from Historical ({cur_rain:.2f} mm vs {bas_rain:.2f} mm Baseline)
            - VEGETATION (NDVI): {ndvi_change:+.1f}% Deviation from Historical ({mean_ndvi:.3f} Season vs {statistics.get('baseline_ndvi', 0):.3f} Baseline)
            - MULTI-PERIL RISK AREA: {multi_peril_risk:,.0f} Hectares
            
            ZONAL COMPARATIVE BREAKDOWN:
            {impact_context}
            
            INSTRUCTIONS:
            1. BE DECISIVE & PERSONALIZED: Start the very first sentence by explicitly naming the region (e.g., "In {region_name}, ...").
            2. AVOID GENERIC OPENINGS: Do not start with "The report shows..." or "Agricultural conditions...". Lead with the region's current percentage performance.
            3. AVOID DECIMAL OVERLOAD: Do not use technical units like m³/m³ in the summary text. Use percentages for all comparative insights.
            4. FOCUS ON IMPACT: Identify if current deviations are driving yield security or risk.
            5. ACTIONABLE: What is the bottom line for yield security this season?
            6. LEGEND: Briefly mention that map colors indicate Soil Moisture Anomaly.
            7. LIMIT: Maximum 160 words. No markdown headers. One cohesive, executive paragraph.
            """
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a professional agricultural GIS consultant for Yieldera Net."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7
                },
                timeout=25
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
            else:
                return f"Analysis complete. However, AI summary generation failed (Status: {response.status_code})."
                
        except Exception as e:
            return f"Analysis complete. AI Commentary generation error: {str(e)}"

# Global instance
ai_intel = AIIntelligence()
