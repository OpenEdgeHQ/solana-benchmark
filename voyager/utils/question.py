from typing import Dict, Any
from pathlib import Path
import json
import random

from voyager.surfpool_env import SurfpoolEnv
from voyager.utils.parameter_generator import ParameterGenerator, format_parameter_value

class QuestController:
    """Quest Controller - Coordinate single round transaction generation evaluation"""

    def __init__(
        self,
        question_path: str | None,
        question_bench: str,
    ):
        self.question_paths = {}
        self.question_benches = {}
        self.parameter_generator = ParameterGenerator()
        if question_path and Path(question_path).exists():
            self._find_question_files(question_path, self.question_paths)
        if question_bench and Path(question_bench).exists():
            self._find_question_files(question_bench, self.question_benches)
        else:
            raise FileNotFoundError(f"Bench dir not found: {question_bench}")

    def _find_question_files(self, path, container):
        for dir in Path(path).iterdir():
            if dir.is_file() and dir.name.endswith(".json"):
                container[dir.name.replace(".json", "")] = dir
            elif dir.is_dir():
                self._find_question_files(dir, container)

    def _load_question(self, question_name: str | None, env: SurfpoolEnv) -> Dict[str, Any]:
        """Load question configuration"""
        # Random pick question if not specified
        quest_names = list(self.question_paths.keys())
        if not question_name:
            question_name = random.choice(quest_names)
        elif question_name not in quest_names:
            raise FileNotFoundError(f"Question not found: {question_name}")
        
        question_file = Path(self.question_paths[question_name])
        if not question_file.exists():
            raise FileNotFoundError(f"Question not found: {question_name}")
        
        with open(question_file, 'r', encoding='utf-8') as f:
            quest = json.load(f)
            for param_name, param_obj in quest["parameters"].items():
                if (
                    param_obj.get("type") == "address" 
                    and param_obj["generation"].get("method") == "from_list"
                    and len(param_obj["generation"].get("addresses", [])) == 0
                ):
                    if param_name.startswith("token_address"):
                        quest["parameters"][param_name]["generation"]["addresses"] = env.token_mints
                    elif param_name.startswith("nft_address"):
                        quest["parameters"][param_name]["generation"]["addresses"] = env.nft_mints
            return quest

    def _generate_parameters(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Generate random parameter values based on question configuration"""
        if not question.get('parameters'):
            return {}
        
        return self.parameter_generator.generate_parameters(question['parameters'])

    def _fill_validation_params(self, question: Dict[str, Any], param_name: str, param_value: Any):
        # Fill parameters for automic problems
        if "validation" in question:
            for rule in question["validation"].get("post_conditions", []):
                if "expected" in rule and rule["expected"] == f"{{{param_name}}}":
                    if param_name == "percentage":
                        rule["expected"] = f"{param_value / 100}"
                    else:
                        rule["expected"] = f"{param_value}"
                if rule.get("owner", "") == f"{{{param_name}}}":
                    rule["owner"] = f"{param_value}"
                if rule.get("mint", "") == f"{{{param_name}}}":
                    rule["mint"] = f"{param_value}"

    def _generate_natural_language_prompt(self, question: Dict[str, Any], env: SurfpoolEnv) -> str:
        """Generate natural language prompt with filled parameters"""
        templates = question.get('natural_language_templates', [])
        if not templates:
            raise ValueError("No natural language templates defined for this question")
        
        # Choose a random template
        template = random.choice(templates)

        # Get all atomic operations of composite problem
        composite_sub_ops = []
        if question["category"] == "composite_problems" and "composite_structure" in question:
            composite_sub_ops = question["composite_structure"]["atomic_operations"]
            # Load sub question data
            for op in composite_sub_ops:
                op["question"] = self._load_question(op["atomic_id"], env)
        
        # Fill in the parameters
        generated_params = self._generate_parameters(question)
        for param_name, param_value in generated_params.items():
            param_config = question['parameters'][param_name]
            self._fill_validation_params(question, param_name, param_value)
            # Fill parameters for composite problems
            for op in composite_sub_ops:
                # Load sub question data
                for sub_param_name, sub_param_placeholder in op["parameter_mapping"].items():
                    if sub_param_placeholder == param_name:
                        self._fill_validation_params(op["question"], sub_param_name, param_value)
                    elif sub_param_placeholder == "agent_address":
                        self._fill_validation_params(op["question"], sub_param_name, str(env.agent_keypair.pubkey()))

            formatted_value = format_parameter_value(param_value, param_config)
            template = template.replace(f"{{{param_name}}}", formatted_value)

        return template