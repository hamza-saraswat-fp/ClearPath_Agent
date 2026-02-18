"""Excel generation endpoint."""

import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ...models.intent_schemas import StructuredIntent
from ...services.config_to_excel import ConfigToExcelConverter
from ...services.excel_generator import ExcelGenerator
from ...services.intent_transformer import IntentTransformer
from ..schemas import PipelineError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/generate",
    response_class=FileResponse,
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
            "description": "Generated ClearPath import template (.xlsx)",
        },
        422: {
            "model": PipelineError,
            "description": "Validation error in input or pipeline",
        },
        500: {
            "model": PipelineError,
            "description": "Internal pipeline error during generation",
        },
    },
    summary="Generate ClearPath Excel template",
    description="Takes a StructuredIntent JSON and returns a FieldPulse ClearPath import template (.xlsx file).",
)
def generate_excel(intent: StructuredIntent) -> FileResponse:
    """Generate a ClearPath Excel import template from StructuredIntent.

    Pipeline: StructuredIntent -> IntentTransformer -> ConfigToExcelConverter -> ExcelGenerator -> .xlsx
    """
    try:
        # Step 1: Transform intent to StatusActionFlow
        transformer = IntentTransformer()
        flow = transformer.transform(intent)
        logger.info(
            f"Transformed '{intent.workflow_name}' -> {len(flow.statuses)} statuses"
        )

        # Step 2: Convert to Excel template schema
        converter = ConfigToExcelConverter()
        template = converter.convert(flow)
        logger.info(
            f"Converted to template: {len(template.action_buttons)} buttons, "
            f"{len(template.focus_view)} focus rows"
        )

        # Step 3: Generate Excel file to temp directory
        generator = ExcelGenerator(default_output_dir=Path(tempfile.gettempdir()))
        output_path = generator.generate(
            template,
            output_path=None,
            overwrite=True,
            validate_first=True,
        )
        logger.info(f"Generated Excel: {output_path}")

        # Build download filename
        safe_name = "".join(
            c if c.isalnum() or c in "-_ " else "_" for c in intent.workflow_name
        ).replace(" ", "_")
        download_filename = f"ClearPath_Import_{safe_name}.xlsx"

        return FileResponse(
            path=str(output_path),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=download_filename,
            headers={
                "X-Workflow-Name": intent.workflow_name,
                "X-Status-Count": str(len(flow.statuses)),
                "X-Button-Count": str(len(template.action_buttons)),
            },
            background=BackgroundTask(os.unlink, str(output_path)),
        )

    except ValueError as e:
        logger.warning(f"Pipeline validation error: {e}")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": str(e),
                "stage": "pipeline",
            },
        )
    except Exception as e:
        logger.exception(f"Pipeline error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "pipeline_error",
                "message": f"Failed to generate Excel template: {str(e)}",
                "stage": "generation",
            },
        )
