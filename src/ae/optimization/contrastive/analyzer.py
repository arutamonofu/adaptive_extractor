import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Callable, Optional, Any
import dspy
from pydantic import ValidationError

from ae.core.tasks.config import TaskConfig
from ae.core.storage.ground_truth import _normalize_document_key
from ae.optimization.contrastive.models import AnalysisInput, DocumentAnalysis, FieldSpecSummary

logger = logging.getLogger(__name__)


class AnalyzeDocumentSignature(dspy.Signature):
    """Placeholder — overwritten dynamically by LocalAnalyzer._build_prompt_instruction()."""
    article_text: str = dspy.InputField(desc="Full text of the scientific article in Markdown format")
    ground_truth_json: str = dspy.InputField(desc="JSON array of Ground Truth experiments for this article")
    initial_instruction: str = dspy.InputField(desc="The baseline extraction prompt/instruction originally given to the curators")
    field_schema: str = dspy.InputField(desc="Full YAML schema with field descriptions and constraints")
    global_dataset_snapshot: str = dspy.InputField(desc="Baseline reality: a statistical snapshot of the entire GT dataset to prevent false generalizations")
    analysis: DocumentAnalysis = dspy.OutputField(desc="Structured hierarchical analysis result conforming to DocumentAnalysis schema")


class LocalAnalyzer:
    """Анализирует отдельную пару документ-GT для извлечения наблюдений (observations) с гарантией валидности JSON и кэшированием."""

    def __init__(
        self, 
        lm: dspy.LM, 
        task_config: TaskConfig, 
        cache_dir: str = "data/analysis", 
        instruction_text: str = "",
        schema_text: str = "",
        global_snapshot: Optional[Dict[str, Any]] = None,
        rate_limit_delay: float = 10.0
    ):
        self.lm = lm
        self.task_config = task_config
        self.cache_dir = Path(cache_dir)
        self.instruction_text = instruction_text
        self.schema_text = schema_text
        self.global_snapshot = global_snapshot or {}
        self.rate_limit_delay = rate_limit_delay
        self.predictor = dspy.Predict(AnalyzeDocumentSignature)

    def _build_prompt_instruction(self, error_context: Optional[str] = None) -> str:
        """Формирует расширенную системную инструкцию со строго заданной матрицей вопросов и контекстом."""
        instruction = (
            "You are an expert data engineer and scientist specializing in chemical informatics and structured information extraction.\n"
            "Your task is to perform a strict contrastive audit to reverse-engineer the hidden extraction rules applied by human curators.\n"
            "You are provided with:\n"
            "1. The raw scientific article (`article_text`).\n"
            "2. The actual extraction result (`ground_truth_json`).\n"
            "3. The original instruction given to the curator (`initial_instruction`).\n"
            "4. The strict schema definitions (`field_schema`).\n"
            "5. A statistical snapshot of the entire dataset (`global_dataset_snapshot`).\n\n"
            "Analyze the gap between the raw text, the instruction, and the Ground Truth by answering the following systematic matrix:\n\n"
            "1. ENTITY-LEVEL ANALYSIS (Row Filtration Logic):\n"
            "   - Identify what specific experiments/entities WERE extracted (included=true) and what similar entities were DELIBERATELY OMITTED (included=false).\n"
            "   - Map these to `EntityObservation` objects. Provide direct quotes as `evidence`.\n"
            "   - VERY IMPORTANT: Use the `global_dataset_snapshot` as your Baseline Reality. If you notice an entity is omitted in this article, but the snapshot shows it is widely extracted in the global dataset, do NOT assume a global ban. Find the specific textual/contextual reason it was omitted in THIS specific document.\n\n"
            "2. FIELD-LEVEL ANALYSIS (Column Logic) -> MUST BE NESTED INSIDE INCLUDED ENTITIES:\n"
            "   - FOR EACH `included=true` entity ONLY, analyze its fields. How did the raw text transform into the GT value?\n"
            "   - Did the curator convert units to match the schema? Did they drop standard deviations (±)?\n"
            "   - Map these to `FieldObservation` objects INSIDE the parent `EntityObservation`'s `field_observations` list.\n"
            "   - Categorize using: 'extraction_included', 'extraction_excluded', 'format_applied', 'format_rejected'.\n"
            "   - Include the 'field_name', rule 'description', 'evidence' (quote), and final 'gt_value' for each observation.\n\n"
            "CRITICAL CONSTRAINTS:\n"
            "- Do not hallucinate. Every deduced rule must be backed by direct quotes/evidence from the article text.\n"
            "- Do not generate `field_observations` for entities where `included=false`.\n"
            "- Your output must strictly conform to the hierarchical DocumentAnalysis JSON schema."
        )

        if error_context:
            instruction += (
                f"\n\n[WARNING: Your previous attempt failed validation with the following error:\n{error_context}\n"
                f"Analyze the error, fix the structure, and ensure 100% strict JSON/Pydantic compliance without any markdown wrappers!]"
            )

        return instruction

    async def analyze(self, input_data: AnalysisInput) -> DocumentAnalysis:
        """Выполняет LLM-анализ одного документа с поддержкой кэширования и повторных запросов."""
        task_name = self.task_config.name
        cache_path = self.cache_dir / f"{task_name}_map_{input_data.document_id}.json"
        
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                validated_data = DocumentAnalysis.model_validate(cached_data)
                logger.info(f"Использован кэш для документа {input_data.document_id} из {cache_path}")
                return validated_data
            except Exception as e:
                logger.warning(
                    f"Кэш для документа {input_data.document_id} в {cache_path} поврежден или невалиден: {e}. "
                    f"Запускаем повторный анализ через LLM."
                )

        if self.rate_limit_delay > 0:
            logger.info(f"Ожидание {self.rate_limit_delay} секунд перед запросом к LLM для {input_data.document_id}...")
            await asyncio.sleep(self.rate_limit_delay)

        if self.schema_text:
            schema_str = self.schema_text
        else:
            schema_str = json.dumps(
                {k: v.model_dump() for k, v in input_data.field_specs.items()},
                ensure_ascii=False
            )
            
        gt_json_str = json.dumps(input_data.ground_truth_experiments, ensure_ascii=False)
        global_snapshot_str = json.dumps(self.global_snapshot, ensure_ascii=False)
        
        max_retries = 2
        validation_error_feedback = ""
        
        for attempt in range(max_retries + 1):
            try:
                current_instruction = self._build_prompt_instruction(validation_error_feedback)
                DynamicAnalyzeSignature = type(
                    "DynamicAnalyzeSignature",
                    (AnalyzeDocumentSignature,),
                    {"__doc__": current_instruction}
                )

                self.predictor = dspy.Predict(DynamicAnalyzeSignature)

                with dspy.settings.context(lm=self.lm):
                    prediction = self.predictor(
                        article_text=input_data.document_text,
                        ground_truth_json=gt_json_str,
                        initial_instruction=self.instruction_text or "No instruction provided.",
                        field_schema=schema_str,
                        global_dataset_snapshot=global_snapshot_str
                    )
                
                analysis_result = prediction.analysis
                if isinstance(analysis_result, DocumentAnalysis):
                    validated_data = analysis_result
                elif isinstance(analysis_result, dict):
                    validated_data = DocumentAnalysis.model_validate(analysis_result)
                elif isinstance(analysis_result, str):
                    clean_str = analysis_result.strip()
                    if clean_str.startswith("```"):
                        lines = clean_str.splitlines()
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].startswith("```"):
                            lines = lines[:-1]
                        clean_str = "\n".join(lines).strip()
                    
                    parsed_dict = json.loads(clean_str)
                    validated_data = DocumentAnalysis.model_validate(parsed_dict)
                else:
                    validated_data = DocumentAnalysis.model_validate(analysis_result)
                
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                temp_path = cache_path.with_suffix(".tmp")
                try:
                    with open(temp_path, "w", encoding="utf-8") as f:
                        json.dump(validated_data.model_dump(), f, ensure_ascii=False, indent=2)
                    temp_path.replace(cache_path)
                    logger.info(f"Анализ документа {input_data.document_id} успешно записан в кэш: {cache_path}")
                except Exception as e:
                    logger.error(f"Не удалось записать кэш для документа {input_data.document_id}: {e}")
                    if temp_path.exists():
                        temp_path.unlink()
                
                return validated_data
                
            except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as e:
                logger.warning(
                    f"Попытка {attempt + 1}/{max_retries + 1} для {input_data.document_id} "
                    f"завершилась ошибкой валидации: {e}"
                )
                validation_error_feedback = f"Ошибка валидации Pydantic/JSON: {str(e)}"
                
                if attempt == max_retries:
                    logger.error(
                        f"Не удалось получить валидный JSON для {input_data.document_id} после {max_retries} повторов."
                    )
                    raise e


class ContrastiveMapRunner:
    """Запускает Map-фазу пакетно для списка документов с ограничением конкурентности."""

    def __init__(self, analyzer: LocalAnalyzer, max_concurrent: int = 1):
        self.analyzer = analyzer
        self.max_concurrent = max_concurrent

    async def run_batch(
        self,
        inputs: List[AnalysisInput],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[DocumentAnalysis]:
        """Последовательно или конкурентно запускает анализ с сохранением порядка."""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        completed_count = 0

        async def _run_one(inp: AnalysisInput, idx: int):
            nonlocal completed_count
            async with semaphore:
                try:
                    res = await self.analyzer.analyze(inp)
                except Exception as e:
                    logger.error(f"Ошибка при анализе документа {inp.document_id}: {e}")
                    res = DocumentAnalysis(
                        document_id=inp.document_id,
                        entity_observations=[],
                        summary=f"Ошибка анализа: {str(e)}"
                    )
                finally:
                    if progress_callback:
                        completed_count += 1
                        progress_callback(completed_count, len(inputs))
                return res

        tasks = [_run_one(inp, i) for i, inp in enumerate(inputs)]
        return list(await asyncio.gather(*tasks))


def prepare_analysis_inputs(
    task_config: TaskConfig,
    document_ids: List[str],
    documents: Dict[str, str],            # normalized_doc_key -> markdown_text
    gt_data: Dict[str, List[Dict[str, Any]]],  # normalized_doc_key -> list of GT rows
) -> List[AnalysisInput]:
    """Преобразует сырые данные из репозиториев во входные структуры AnalysisInput."""
    field_specs = {
        name: FieldSpecSummary.from_field_spec(name, spec)
        for name, spec in task_config.experiment_fields.items()
    }

    inputs = []
    for doc_id in document_ids:
        normalized_key = _normalize_document_key(doc_id)

        if normalized_key not in documents:
            logger.warning(
                f"Документ '{doc_id}' (нормализован: '{normalized_key}') "
                f"не найден в parsed_dir, пропускаем"
            )
            continue

        raw_gt = gt_data.get(normalized_key, [])
        doc_gt = [
            exp.model_dump() if hasattr(exp, "model_dump") else dict(exp)
            for exp in raw_gt
        ]
        if not doc_gt:
            logger.warning(
                f"Ground Truth для документа '{doc_id}' (ключ: '{normalized_key}') "
                f"не найден в gt_data. Доступные ключи GT: {sorted(gt_data.keys())[:10]}"
            )

        inputs.append(AnalysisInput(
            document_id=doc_id,
            document_text=documents[normalized_key],
            ground_truth_experiments=doc_gt,
            field_specs=field_specs
        ))
    return inputs