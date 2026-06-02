import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Callable, Optional, Any
import dspy
from pydantic import ValidationError

from ae.core.tasks.config import TaskConfig
from ae.optimization.contrastive.models import AnalysisInput, DocumentAnalysis, FieldSpecSummary

logger = logging.getLogger(__name__)


class AnalyzeDocumentSignature(dspy.Signature):
    """Placeholder — overwritten dynamically by LocalAnalyzer._build_prompt_instruction()."""
    article_text: str = dspy.InputField(desc="Full text of the scientific article in Markdown format")
    ground_truth_json: str = dspy.InputField(desc="JSON array of Ground Truth experiments for this article")
    field_schema: str = dspy.InputField(desc="Field extraction specification as JSON (names, types, constraints)")
    analysis: DocumentAnalysis = dspy.OutputField(desc="Structured analysis result conforming to DocumentAnalysis schema")


class LocalAnalyzer:
    """Анализирует отдельную пару документ-GT для извлечения наблюдений (observations) с гарантией валидности JSON и кэшированием."""

    def __init__(self, lm: dspy.LM, task_config: TaskConfig, cache_dir: str = "data/analysis", rate_limit_delay: float = 10.0):
        self.lm = lm  # Используется teacher LM из конфигурации (qwen3.5-397b-a17b)
        self.task_config = task_config
        self.cache_dir = Path(cache_dir)
        self.rate_limit_delay = rate_limit_delay
        # Предиктор будет пересоздан динамически в analyze() перед каждым вызовом
        self.predictor = dspy.Predict(AnalyzeDocumentSignature)

    def _build_prompt_instruction(self, error_context: Optional[str] = None) -> str:
        """Формирует расширенную системную инструкцию со строго заданной матрицей вопросов."""
        instruction = (
            "You are an expert data engineer and scientist specializing in chemical informatics and structured information extraction.\n"
            "Your task is to perform a strict contrastive audit and reverse-engineer the hidden extraction rules applied by human curators.\n"
            "You will be given the full text of a scientific article (in Markdown), a JSON array of ideal Ground Truth (GT) experiments "
            "extracted from this article, and the target field schema specification.\n\n"
            "Analyze the gap between the raw text and the provided Ground Truth by answering the following systematic matrix:\n\n"
            "1. ENTITY-LEVEL ANALYSIS (Row Filtration Logic) -> Map to `EntityObservation` objects:\n"
            "   - What WAS extracted? (included=true) Identify shared context and inclusion criteria. Provide direct quote as `evidence`.\n"
            "   - What was NOT extracted? (included=false) Find similar entities deliberately omitted. Deduce the exact exclusion boundary. Provide `evidence`.\n\n"
            "2. FIELD-LEVEL ANALYSIS (Column Logic for EACH schema field) -> Map to `FieldObservation` objects:\n"
            "   For each field, deduce the rules and categorize them using strictly these `observation_type`s:\n"
            "   - 'extraction_included': Why a specific value was extracted.\n"
            "   - 'extraction_excluded': Why context was present but left null/empty in GT (e.g., ambiguous data).\n"
            "   - 'format_applied': How raw text was transformed into the final GT value (e.g., unit conversion to mM, rounding).\n"
            "   - 'format_rejected': How it COULD have been recorded based on raw text but wasn't (e.g., discarding ± error margins).\n"
            "   Include the 'field_name', rule 'description', 'evidence' (quote), and final 'gt_value' for each observation.\n\n"
            "CRITICAL CONSTRAINTS:\n"
            "- Do not hallucinate. Every deduced rule must be backed by direct quotes/evidence from the article text.\n"
            "- Your output must strictly conform to the DocumentAnalysis JSON schema."
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
        
        # 1. Проверяем наличие валидного локального кэша перед вызовом LLM
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

        field_schema_str = json.dumps(
            {k: v.model_dump() for k, v in input_data.field_specs.items()},
            ensure_ascii=False
        )
        gt_json_str = json.dumps(input_data.ground_truth_experiments, ensure_ascii=False)
        
        max_retries = 2
        validation_error_feedback = ""
        
        for attempt in range(max_retries + 1):
            try:
                # Динамически и безопасно создаем изолированный класс сигнатуры для этой попытки
                current_instruction = self._build_prompt_instruction(validation_error_feedback)
                DynamicAnalyzeSignature = type(
                    "DynamicAnalyzeSignature",
                    (AnalyzeDocumentSignature,),
                    {"__doc__": current_instruction}
                )

                # Пересоздаем предиктор с изолированной сигнатурой
                self.predictor = dspy.Predict(DynamicAnalyzeSignature)

                with dspy.settings.context(lm=self.lm):
                    prediction = self.predictor(
                        article_text=input_data.document_text,
                        ground_truth_json=gt_json_str,
                        field_schema=field_schema_str
                    )
                
                # Дополнительная строгая рантайм-валидация через Pydantic
                analysis_result = prediction.analysis
                if isinstance(analysis_result, DocumentAnalysis):
                    validated_data = analysis_result
                elif isinstance(analysis_result, dict):
                    validated_data = DocumentAnalysis.model_validate(analysis_result)
                elif isinstance(analysis_result, str):
                    import re
                    # Безопасно очищаем маркдаун-обертку ```json ... ``` и парсим JSON
                    match = re.search(r'```(?:json)?\s*(.*?)\s*```', analysis_result, re.DOTALL)
                    clean_str = match.group(1) if match else analysis_result.strip()
                    parsed_dict = json.loads(clean_str)
                    validated_data = DocumentAnalysis.model_validate(parsed_dict)
                else:
                    validated_data = DocumentAnalysis.model_validate(analysis_result)
                
                # 2. Атомарное сохранение результата в кэш сразу после успешной генерации
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
        self.max_concurrent = max_concurrent  # По умолчанию 1 из-за жестких rate-limits у API

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
                        field_observations=[],
                        summary=f"Ошибка анализа: {str(e)}"
                    )
                finally:
                    if progress_callback:
                        completed_count += 1
                        progress_callback(completed_count, len(inputs))
                return res

        # asyncio.gather автоматически возвращает результаты в исходном порядке
        tasks = [_run_one(inp, i) for i, inp in enumerate(inputs)]
        return list(await asyncio.gather(*tasks))


def prepare_analysis_inputs(
    task_config: TaskConfig,
    document_ids: List[str],
    documents: Dict[str, str],            # doc_id -> markdown_text
    gt_data: Dict[str, List[Dict[str, Any]]],  # doc_id -> list of GT rows
) -> List[AnalysisInput]:
    """Преобразует сырые данные из репозиториев во входные структуры AnalysisInput."""
    field_specs = {
        name: FieldSpecSummary.from_field_spec(name, spec)
        for name, spec in task_config.experiment_fields.items()
    }
    
    inputs = []
    for doc_id in document_ids:
        if doc_id not in documents:
            logger.warning(f"Документ {doc_id} не найден в parsed_dir, пропускаем")
            continue
            
        doc_gt = gt_data.get(doc_id, [])
        inputs.append(AnalysisInput(
            document_id=doc_id,
            document_text=documents[doc_id],
            ground_truth_experiments=doc_gt,
            field_specs=field_specs
        ))
    return inputs
