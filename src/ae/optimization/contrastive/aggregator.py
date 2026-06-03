import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import dspy

from ae.core.tasks.config import TaskConfig
from ae.optimization.contrastive.models import (
    DocumentAnalysis,
    AnalysisResult,
    VerifiedRule,
    Discrepancy,
)

logger = logging.getLogger(__name__)


class SemanticEquivalenceChecker(dspy.Signature):
    """
    You are a strict logic arbiter (Zero-Tolerance Consensus Judge).
    You will be provided with a list of natural language rule formulations extracted from multiple scientific papers for a SINGLE specific field or entity.
    These rules were formulated by independent local AI agents.
    You are also provided with a `global_dataset_snapshot` which represents the baseline reality of the entire Ground Truth dataset.

    ANALYSIS PROTOCOL:
    1. Read all rule formulations provided in the input list.
    2. Ignore syntax, grammar, and synonyms (e.g., 'converted to Celsius' and 'format changed to °C' are logically identical).
    3. Verify against the global_dataset_snapshot: If the local rules propose a strict ban or exclusion of something that ACTUALLY EXISTS in the global snapshot, this is a false generalization.
    4. Determine if ALL rules enforce the exact same extraction and formatting logic without any contradictions, AND they do not conflict with the global baseline reality.

    OUTPUT PROTOCOL:
    - is_unanimous (bool): True ONLY IF 100% of the formulations mean the exact same thing logically AND align with the global reality. False if there is even one contradiction, alternative condition, or conflict with the global snapshot.
    - consolidated_rule (str): If is_unanimous is True, synthesize a single, clear, imperative-mood instruction in English (e.g., 'Always convert temperature to Celsius'). If False, output an empty string.
    - discrepancy_description (str): If is_unanimous is False, write a detailed explanation of the logical conflict (e.g., '8 agents ignored values without units, but the global snapshot shows they are actually valid'). If True, output an empty string.
    """

    context_name: str = dspy.InputField(desc="The name of the schema field being evaluated, or 'ENTITY_LEVEL'.")
    rule_formulations: str = dspy.InputField(desc="List of textual rules extracted from different documents.")
    global_dataset_snapshot: str = dspy.InputField(desc="Statistical snapshot of the entire GT dataset.")

    is_unanimous: bool = dspy.OutputField(desc="True if 100% logical consensus is reached, otherwise False.")
    consolidated_rule: str = dspy.OutputField(desc="The unified rule if unanimous, otherwise empty.")
    discrepancy_description: str = dspy.OutputField(desc="Description of the conflict if not unanimous, otherwise empty.")



def extract_json(text: str) -> Any:
    """Extract the first valid JSON array or object from text by brace/bracket balancing."""
    text_to_search = text.strip()
    start_arr = text_to_search.find("[")
    start_obj = text_to_search.find("{")
    
    if start_arr == -1 and start_obj == -1:
        raise ValueError("No JSON block found in the output: " + text)
        
    start = start_arr if (start_obj == -1 or (start_arr != -1 and start_arr < start_obj)) else start_obj
    char_open = text_to_search[start]
    char_close = "]" if char_open == "[" else "}"
    
    depth = 0
    in_string = False
    escape_next = False
    
    for i in range(start, len(text_to_search)):
        ch = text_to_search[i]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == char_open:
            depth += 1
        elif ch == char_close:
            depth -= 1
            if depth == 0:
                json_str = text_to_search[start:i+1]
                return json.loads(json_str)
    raise ValueError("Unbalanced JSON braces/brackets in the output")


class StrictAggregator:
    """Агрегирует наблюдения и формирует итоговый набор верифицированных правил через точечный семантический судью."""

    def __init__(
        self, 
        lm: dspy.LM, 
        task_config: TaskConfig, 
        cache_dir: str = "data/analysis",
        global_snapshot: Optional[Dict[str, Any]] = None
    ):
        self.lm = lm
        self.task_config = task_config
        self.cache_dir = Path(cache_dir)
        self.global_snapshot = global_snapshot or {}
        self.predictor = dspy.Predict(SemanticEquivalenceChecker)

    def aggregate(self, analyses: List[DocumentAnalysis]) -> AnalysisResult:
        """Агрегирует наблюдения по всем проанализированным документам через точечный семантический судью."""
        num_documents = len(analyses)
        if num_documents < 5:
            logger.warning(
                f"Мало документов для анализа: передано {num_documents} документов. "
                f"Консенсус может быть статистически недостоверным."
            )

        # ------------------------------------------------------------------ #
        # Шаг 1: Сбор данных из всех DocumentAnalysis (с учетом иерархии)
        # ------------------------------------------------------------------ #

        # entity-уровень: список (description, doc_id)
        entity_formulations: List[str] = []
        entity_doc_ids: List[str] = []

        # field-уровень: ключ = (field_name, observation_type) -> [(description, doc_id)]
        field_groups: Dict[tuple, List[tuple]] = {}

        for doc_analysis in analyses:
            doc_id = doc_analysis.document_id

            for ent_obs in doc_analysis.entity_observations:
                entity_formulations.append(ent_obs.description)
                entity_doc_ids.append(doc_id)

                # ИЕРАРХИЯ: Извлекаем правила полей только из взятых (included) сущностей
                if getattr(ent_obs, 'included', False):
                    for field_obs in getattr(ent_obs, 'field_observations', []):
                        key = (field_obs.field_name, field_obs.observation_type)
                        if key not in field_groups:
                            field_groups[key] = []
                        field_groups[key].append((field_obs.description, doc_id))

        # ------------------------------------------------------------------ #
        # Шаг 2: Точечные LLM-вызовы через SemanticEquivalenceChecker
        # ------------------------------------------------------------------ #
        verified_rules: List[VerifiedRule] = []
        discrepancies: List[Discrepancy] = []
        
        global_snapshot_str = json.dumps(self.global_snapshot, ensure_ascii=False)

        def _run_checker(
            context_name: str,
            formulations: List[str],
            doc_ids: List[str],
            level: str,
            field_name: Optional[str],
            rule_id_prefix: str,
        ) -> None:
            """Helper: запускает SemanticEquivalenceChecker для одной группы формулировок и
            добавляет VerifiedRule или Discrepancy в соответствующий список."""
            if not formulations:
                return

            try:
                # Оптимизируем формат для LLM: переводим в читаемый markdown-список
                formatted_rules = "\n".join([f"- {desc}" for desc in formulations])

                with dspy.settings.context(lm=self.lm):
                    result = self.predictor(
                        context_name=context_name,
                        rule_formulations=formatted_rules,
                        global_dataset_snapshot=global_snapshot_str
                    )

                # Безопасно парсим булево значение через Pydantic TypeAdapter
                from pydantic import TypeAdapter
                try:
                    is_un = TypeAdapter(bool).validate_python(result.is_unanimous)
                except Exception as parse_err:
                    logger.warning(
                        f"Не удалось распознать булево значение '{result.is_unanimous}' "
                        f"для контекста '{context_name}'. Ошибка: {parse_err}. "
                        f"Принудительно отправляем на ручной разбор."
                    )
                    is_un = False

                if is_un:
                    rule_idx = len(verified_rules)
                    verified_rules.append(VerifiedRule(
                        rule_id=f"{rule_id_prefix}_{rule_idx}",
                        level=level,
                        field_name=field_name,
                        rule_text=result.consolidated_rule or formulations[0],
                        evidence_count=len(formulations),
                        evidence_examples=formulations[:3],
                    ))
                    logger.info(
                        f"[Консенсус достигнут] context='{context_name}', "
                        f"n={len(formulations)} формулировок"
                    )
                else:
                    # Семантические противоречия: примерный consensus_ratio как доля
                    # большинства (0.5 по умолчанию, точная математика LLM-судьёй не ведёт)
                    disc_idx = len(discrepancies)
                    unique_doc_ids = list(dict.fromkeys(doc_ids))  # порядок сохранён
                    discrepancies.append(Discrepancy(
                        discrepancy_id=f"{rule_id_prefix}_disc_{disc_idx}",
                        level=level,
                        field_name=field_name,
                        problem_description=result.discrepancy_description or f"Semantic conflict in '{context_name}'",
                        consensus_ratio=0.5,
                        variant_a=formulations[0] if len(formulations) > 0 else "",
                        variant_b=formulations[1] if len(formulations) > 1 else "",
                        example_documents=unique_doc_ids[:5],
                    ))
                    logger.warning(
                        f"[Противоречие выявлено] context='{context_name}': "
                        f"{result.discrepancy_description!r}"
                    )
            except Exception as e:
                logger.error(
                    f"Ошибка SemanticEquivalenceChecker для context='{context_name}': {e}"
                )

        # --- Entity-level group (ENTITY_LEVEL) ---
        if entity_formulations:
            logger.info(
                f"Агрегация entity-level: {len(entity_formulations)} формулировок из {num_documents} документов"
            )
            _run_checker(
                context_name="ENTITY_LEVEL",
                formulations=entity_formulations,
                doc_ids=entity_doc_ids,
                level="entity",
                field_name=None,
                rule_id_prefix="rule_ent",
            )

        # --- Field-level groups (field_name + observation_type) ---
        for (field_name, obs_type), pairs in field_groups.items():
            formulations = [desc for desc, _ in pairs]
            doc_ids = [did for _, did in pairs]
            context_name = f"{field_name}::{obs_type}"

            logger.info(
                f"Агрегация field-level: context='{context_name}', "
                f"{len(formulations)} формулировок"
            )
            _run_checker(
                context_name=context_name,
                formulations=formulations,
                doc_ids=doc_ids,
                level="field",
                field_name=field_name,
                rule_id_prefix=f"rule_fld_{field_name}_{obs_type}",
            )

        # ------------------------------------------------------------------ #
        # Шаг 3: Формируем итоговый результат
        # ------------------------------------------------------------------ #
        result = AnalysisResult(
            task_name=self.task_config.name,
            analyzed_documents=num_documents,
            verified_rules=verified_rules,
            discrepancies=discrepancies,
            timestamp=datetime.now().isoformat(),
        )
        return result