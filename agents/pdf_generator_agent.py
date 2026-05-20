"""PDF Generator Agent — triggers PDF creation after plan approval."""
import os
from tools.pdf_tool import generate_trip_pdf
from config.settings import OUTPUT_DIR
from state.trip_state import TripState


def pdf_generator_agent(state: TripState) -> dict:
    """Generate the final downloadable PDF report."""
    try:
        filepath = generate_trip_pdf(dict(state), output_dir=OUTPUT_DIR)
        filename = os.path.basename(filepath)
        return {
            "pdf_status": {
                "generated": True,
                "path": filepath,
                "filename": filename,
            },
            "status": "done",
            "messages": [{"role": "system", "content":
                          f"PDF Generator: Report created — {filename}"}],
        }
    except Exception as e:
        return {
            "pdf_status": {"generated": False, "error": str(e)},
            "status": "done",
            "error_log": [f"PDF Generator error: {e}"],
            "messages": [{"role": "system", "content": f"PDF Generator: Error — {e}"}],
        }
