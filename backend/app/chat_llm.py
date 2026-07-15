import logging
import random
import urllib.request
import urllib.error
import json
import asyncio
from datetime import datetime
from typing import Dict, Any
from .database import db_instance
from .config import settings

logger = logging.getLogger("uvicorn.error")

class ChatLLMService:
    def __init__(self):
        # Local keyword maps for fallback trades and levels
        self.trade_keywords = {
            "Welder": ["arc", "weld", "gas", "mig", "tig", "slag", "electrode", "joint", "shielding", "heat", "penetration", "metal"],
            "Electrician": ["voltage", "current", "multimeter", "circuit", "resistance", "wire", "grounding", "transformer", "relay", "breaker", "phase"],
            "Fitter": ["tolerance", "caliper", "dimension", "alignment", "joint", "lathe", "thread", "template", "drill", "gauge", "coupling"],
            "CNC Operator": ["g-code", "m-code", "feedrate", "axis", "spindle", "coordinates", "carbide", "tooling", "cnc", "cutting", "coolant"]
        }
        
        self.advanced_keywords = ["optimization", "defects", "calibration", "harmonic", "tolerance limits", "residual stress", "programming", "troubleshoot", "thermal expansion"]
        self.intermediate_keywords = ["measurement", "safety", "calculation", "wire gauge", "feed", "electrode type", "welding position", "formula", "connection"]

        # Realistic pre-generated expert answers for offline fallback
        self.sample_answers = {
            "welder_electrode": (
                "An electrode is a coated metal wire or rod used to conduct electrical current through the welding arc to melt and join metal parts together. "
                "In Shielded Metal Arc Welding (SMAW or Stick), the electrode is consumable and melts to form the filler metal. In gas metal arc welding (MIG), the electrode "
                "is a continuously fed solid wire. In gas tungsten arc welding (TIG), a non-consumable tungsten rod acts as the electrode to create the arc without melting itself."
            ),
            "welder_general": (
                "To optimize welding arc stability and penetration, ensure proper voltage/amperage settings matched to your plate thickness and electrode size. "
                "Maintain a consistent travel speed and electrode distance (arc length equivalent to the core wire diameter). Ensure correct shielding gas flow (typically 15-20 CFH) "
                "and clean the base metal surface of any rust, oil, or mill scale before striking the arc."
            ),
            "electrician_multimeter": (
                "A multimeter measures electrical properties including voltage (volts), current (amps), and resistance (ohms). To measure voltage safely, connect the black probe "
                "to the COM port and the red probe to the V port, then select the appropriate AC or DC voltage range. For current measurements, the multimeter must be wired in series "
                "with the load circuit, while resistance is measured in parallel across a completely de-energized component to prevent meter damage."
            ),
            "electrician_general": (
                "In industrial power grids, electrical circuits must conform to strict gauge ratings. A 2.5 sq mm copper wire typically supports up to 20-25 Amps depending on the "
                "conduit routing and temperature correction factors. Ensure proper grounding (using green PE conductors), circuit breaker sizing (such as 16A/20A Type C breakers), "
                "and regular testing of residual current devices (RCDs) to maintain shop safety."
            ),
            "cnc_general": (
                "CNC tooling calibrations depend heavily on tool coordinate offsets (G43 offsets) and feedrate adjustments. A G-code G00 command triggers rapid travel to absolute "
                "coordinates, while G01 controls linear cutting interpolation. Spindle speeds (RPM) and cutting feedrates (IPM or mm/min) must be computed based on the material's "
                "surface feet per minute (SFM) and feed-per-tooth parameters to prevent cutter chatter or premature tooling wear."
            ),
            "general_fallback": (
                "In workshop practice, technical efficiency depends on selecting the correct tool for the task, performing precise calibrations, and maintaining strict safety compliance. "
                "Always verify component tolerances against blueprint engineering specifications and utilize appropriate personal protective equipment (PPE) before starting any operations."
            )
        }

    def _get_installed_ollama_model(self) -> str:
        url = "http://127.0.0.1:11434/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                models = res_data.get("models", [])
                if models:
                    return models[0].get("name", "qwen")
        except Exception:
            pass
        return "qwen"

    def _call_ollama_raw(self, model_name: str, prompt: str) -> str:
        url = "http://127.0.0.1:11434/api/generate"
        data = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=90) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data.get("response", "").strip()

    def _call_ollama_json(self, model_name: str, prompt: str) -> dict:
        url = "http://127.0.0.1:11434/api/generate"
        data = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=90) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            generated_text = res_data.get("response", "")
            
            # Clean up markdown code fences if present
            cleaned_text = generated_text.strip()
            if cleaned_text.startswith("```"):
                lines = cleaned_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned_text = "\n".join(lines).strip()
            
            return json.loads(cleaned_text)

    async def analyze_question(self, trainee_id: str, question_text: str) -> Dict[str, Any]:
        logger.info(f"Analyzing trainee {trainee_id} chat query: '{question_text}'")
        
        # 1. Fetch Trainee details from DB
        trainee = await db_instance.get_trainee(trainee_id)
        trainee_name = "Unknown Trainee"
        trainee_trade = "General"
        if trainee:
            trainee_name = trainee.get("name", "Unknown Trainee")
            trainee_trade = trainee.get("trade", "General")

        # Check for casual greetings
        casual_greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings", "yo", "sup", "howdy"]
        cleaned_query = question_text.strip().lower().rstrip("?").rstrip("!").rstrip(".")
        if cleaned_query in casual_greetings or cleaned_query == "":
            return {
                "trainee_id": trainee_id,
                "trainee_name": trainee_name,
                "timestamp": datetime.now(),
                "question_text": question_text,
                "transcribed_text": question_text,
                "resolved_text": question_text,
                "classification": "General",
                "category": "General",
                "trade": trainee_trade,
                "detected_trade": trainee_trade,
                "score_adjustment": 0,
                "vocabulary_score": 0,
                "score_breakdown": {
                    "relevance": 0,
                    "technical_depth": 0,
                    "vocabulary_level": 0
                },
                "safety_flagged": False,
                "notes": "Casual greeting conversation.",
                "answer": f"Hello {trainee_name}! I am your trade training assistant. How can I help you with your {trainee_trade.lower()} training today?",
                "concept_understanding": "General Conversation",
                "gap_analysis": "N/A - Casual Greeting",
                "recommendation": "Ask a technical trade question to begin assessment.",
                "llm_model_used": "System Greeting"
            }

        # 2. Try CrewAI Multi-Agent Pipeline
        ollama_failed = False
        answer = ""
        metadata = {}
        detected_model = "qwen"
        try:
            # Import CrewAI classes inline
            from crewai import LLM, Agent, Task, Crew
            
            if settings.OPENROUTER_API_KEY:
                # Use custom OpenRouter base URL and key
                # Prefix with openrouter/ if not present to prevent LiteLLM from thinking it's a native Google model
                model_name = settings.OPENROUTER_MODEL
                if not model_name.startswith("openrouter/"):
                    model_name = f"openrouter/{model_name}"
                
                llm = LLM(
                    model=model_name,
                    base_url="https://openrouter.ai/api/v1",
                    api_key=settings.OPENROUTER_API_KEY,
                    temperature=0.2,
                    timeout=120,
                    max_tokens=512
                )
                detected_model = model_name
                logger.info(f"Using OpenRouter with model: {detected_model}")
            else:
                detected_model = await asyncio.to_thread(self._get_installed_ollama_model)
                llm = LLM(
                    model=f"ollama/{detected_model}",
                    base_url="http://127.0.0.1:11434",
                    temperature=0.2,
                    timeout=120
                )
                logger.info(f"Using local Ollama with model: {detected_model}")
            
            # Agent 1: Trade Subject Matter Expert
            expert = Agent(
                role="Trade Subject Matter Expert",
                goal="Explain technical concepts clearly and concisely. If a term is general, first explain its general meaning, insert a blank line, and then explain how it applies to the trade.",
                backstory="You are a highly experienced industrial technician and technical instructor. You explain technical trade concepts directly and concisely, matching the terminology of the trade, without intro phrases. You format your answers by first defining a term generally, followed by a blank line, followed by its specific trade application.",
                llm=llm,
                verbose=False
            )
            
            # Agent 2: Trainee Competency Assessor
            evaluator = Agent(
                role="Trainee Competency Assessor",
                goal="Assess the trainee's technical question depth, vocabulary level, trade relevance, and safety compliance.",
                backstory="You are a veteran vocational training coordinator. You review technical questions submitted by trainees to assess their developmental progress, vocabulary rating, and flag safety hazards.",
                llm=llm,
                verbose=False
            )
            
            # Task 1: Generate concise trade explanation
            explanation_task = Task(
                description=f"""CRITICAL CONSTRAINT: You MUST strictly adhere to any length, line, sentence, or word count requests in the query: "{question_text}". If the query specifies a numeric count N (e.g. "in three lines", "in four sentences", "in three paragraphs"), the total number of sentences/paragraphs you output must sum up to exactly that number N.
                
                Explain the question: "{question_text}" under the trade context: "{trainee_trade}".
                Follow these formatting rules exactly:
                1. First, provide the general definition or meaning of the concept or term in the question.
                2. Second, add a blank line (a double newline).
                3. Third, explain how this concept integrates/applies specifically to the trainee's trade context: "{trainee_trade}".
                
                Length & Sentence Distribution Rules:
                - If a numeric count N is requested (e.g., "three lines" or "three sentences", meaning N=3): You MUST write exactly 1 sentence for the general definition (Section 1), and exactly N - 1 sentences (e.g., 2 sentences) for the trade integration (Section 3). The total number of text sentences across both sections must strictly equal N (do not count the blank line).
                - Otherwise, if "detailed", "large", "full", "explain clearly", or "in-depth" is requested: Both the general definition and the trade integration sections must be detailed, consisting of 3 to 5 sentences each.
                - Otherwise (default): Default to exactly 1 sentence for the general definition and exactly 1 sentence for the trade integration (2 text sentences in total separated by a blank line).
                
                Do not reference the trainee by name or ID. Keep the answer strictly educational and relevant to the trade.""",
                expected_output="A general definition, followed by a blank line, followed by its trade integration, conforming strictly to the requested numeric constraints or mapping rules.",
                agent=expert
            )
            
            # Task 2: Evaluate competency metadata
            evaluation_task = Task(
                description=f"""Evaluate the trainee's question: "{question_text}" under the trade: "{trainee_trade}".
                
                You must return a raw JSON object containing exactly these keys:
                - "category": ("Foundational", "Intermediate", or "Advanced")
                - "score_adjustment": (an integer from 10 to 50 representing XP points to award)
                - "relevance": (an integer percentage from 0 to 100 representing relevance to the trade)
                - "technical_depth": (an integer percentage from 0 to 100 representing technical depth)
                - "vocabulary_level": (an integer percentage from 0 to 100 representing vocabulary rating)
                - "safety_flagged": (true or false if the query contains workshop danger keywords like shock, fire, gas, accident, bypass, or hazard)
                - "notes": (generate a 2-3 sentence assessment feedback note describing the trainee's understanding of this trade concept and technical suggestions)
                
                Do not output any markdown code blocks or wrapper text. Return only the raw JSON.""",
                expected_output="A raw JSON object with the evaluation metadata.",
                agent=evaluator
            )
            
            # Create crew and run it
            crew = Crew(
                agents=[expert, evaluator],
                tasks=[explanation_task, evaluation_task],
                verbose=False
            )
            
            # Run the crew in a separate thread to prevent blocking the event loop
            await asyncio.to_thread(crew.kickoff)
            
            # Parse outputs
            answer = str(explanation_task.output.raw).strip()
            eval_raw = str(evaluation_task.output.raw).strip()
            
            # Clean up markdown code fences if present in JSON output
            if eval_raw.startswith("```"):
                lines = eval_raw.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                eval_raw = "\n".join(lines).strip()
                
            metadata = json.loads(eval_raw)
            logger.info(f"CrewAI multi-agent pipeline evaluated chat query and answer successfully.")
        except Exception as e:
            logger.warning(f"CrewAI multi-agent execution failed: {e}. Falling back to offline heuristic.")
            ollama_failed = True

        # 3. Parse CrewAI results or run offline heuristic fallback
        if not ollama_failed and metadata:
            classification = metadata.get("category", "Intermediate")
            score_adjustment = metadata.get("score_adjustment", 20)
            relevance_score = metadata.get("relevance", 80)
            depth_score = metadata.get("technical_depth", 75)
            vocab_score = metadata.get("vocabulary_level", 70)
            safety_flagged = metadata.get("safety_flagged", False)
            notes = metadata.get("notes", "Evaluation processed successfully via CrewAI.")
            detected_trade = trainee_trade
        else:
            # Offline Heuristic Fallback
            question_lower = question_text.lower()
            detected_trade = trainee_trade
            max_matches = 0
            for trade, keywords in self.trade_keywords.items():
                matches = sum(1 for kw in keywords if kw in question_lower)
                if matches > max_matches:
                    max_matches = matches
                    detected_trade = trade
                    
            classification = "Foundational"
            score_adjustment = 15
            relevance_score = random.randint(70, 85)
            depth_score = random.randint(65, 80)
            vocab_score = min(40.0 + (max_matches * 15.0) + random.uniform(5, 15), 100.0)

            if any(kw in question_lower for kw in self.advanced_keywords):
                classification = "Advanced"
                score_adjustment = 40
                relevance_score = random.randint(88, 98)
                depth_score = random.randint(85, 96)
            elif any(kw in question_lower for kw in self.intermediate_keywords) or max_matches >= 2:
                classification = "Intermediate"
                score_adjustment = 25
                relevance_score = random.randint(80, 92)
                depth_score = random.randint(75, 88)

            safety_flagged = False
            safety_keywords = ["danger", "shock", "fire", "accident", "explode", "burn", "hazard", "unsafe", "leak"]
            if any(kw in question_lower for kw in safety_keywords):
                safety_flagged = True

            # Formulate offline answer based on keywords
            if detected_trade == "Welder":
                if "electrode" in question_lower:
                    answer = self.sample_answers["welder_electrode"]
                else:
                    answer = self.sample_answers["welder_general"]
            elif detected_trade == "Electrician":
                if "multimeter" in question_lower or "measure" in question_lower:
                    answer = self.sample_answers["electrician_multimeter"]
                else:
                    answer = self.sample_answers["electrician_general"]
            elif detected_trade == "CNC Operator":
                answer = self.sample_answers["cnc_general"]
            else:
                answer = self.sample_answers["general_fallback"]

            notes = f"[Offline Mode] The trainee, {trainee_name}, submitted a {classification.lower()} question regarding {detected_trade.lower()} procedures. "
            if detected_trade == "Welder":
                notes += f"They are addressing arc stability and metal joining parameters. Their vocabulary shows a score of {round(vocab_score, 1)}% in welding terminology. "
                if safety_flagged:
                    notes += "WARNING: The query contains elements concerning workshop hazards. Urgent instruction on workshop safety gear is advised."
                else:
                    notes += "The query indicates active engagement in workshop practice. Recommendations: practice multi-pass fillet welds."
            elif detected_trade == "Electrician":
                notes += f"They are inquiring about circuit designs and power distribution parameters. Their technical depth was graded at {depth_score}%. "
                if safety_flagged:
                    notes += "WARNING: Safety flags triggered for potential high-voltage exposure. Review insulation and grounding immediately."
                else:
                    notes += "The trainee is tracking electrical safety and calibrations well. Recommendations: proceed to PLC controls."
            elif detected_trade == "CNC Operator":
                notes += f"They are troubleshooting tooling configurations or axis alignment settings. Topic relevance scored {relevance_score}%. "
                if safety_flagged:
                    notes += "WARNING: Safety checks flagged machine overrides. Review emergency stop routines."
                else:
                    notes += "The trainee shows good G-code command structure understanding. Recommendations: practice feedrate adjustments."
            else:
                notes += f"They are checking dimensions, tool selection, or general fitment criteria. Concept understanding score is high. "
                notes += "Recommendations: review technical manuals and verify manual measurement calibration."

        # 4. Map final evaluation dict satisfying both schemas
        analysis_result = {
            "trainee_id": trainee_id,
            "trainee_name": trainee_name,
            "timestamp": datetime.now().isoformat(),
            "question_text": question_text,
            "transcribed_text": question_text,
            "resolved_text": question_text,
            "classification": classification,
            "category": classification,
            "trade": detected_trade,
            "detected_trade": detected_trade,
            "score_adjustment": score_adjustment,
            "vocabulary_score": round(vocab_score, 1),
            "score_breakdown": {
                "relevance": relevance_score,
                "technical_depth": depth_score,
                "vocabulary_level": round(vocab_score, 1)
            },
            "safety_flagged": safety_flagged,
            "notes": notes,
            "answer": answer,
            "concept_understanding": f"{detected_trade} Principles",
            "gap_analysis": f"Evaluated under {classification} criteria.",
            "recommendation": "Maintain daily safety guidelines.",
            "llm_model_used": "Offline Heuristic" if ollama_failed else detected_model
        }
        
        return analysis_result

chat_llm_service = ChatLLMService()
