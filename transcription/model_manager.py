"""
Local Whisper model management and caching service for LocalStudy.
Ensures models are stored locally for air-gapped offline inference.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

from config.constants import WHISPER_MODELS, DEFAULT_MODELS_DIR
from config.settings import settings
from utils.filesystem import ensure_dir, format_bytes
from utils.logger import logger


class ModelManager:
    """Discovers, tracks, and downloads local speech recognition models."""

    def __init__(self, models_dir: Optional[Path | str] = None):
        if models_dir is None:
            self.models_dir = Path(settings.get("models_dir", str(DEFAULT_MODELS_DIR)))
        else:
            self.models_dir = Path(models_dir)
        ensure_dir(self.models_dir)

    def get_models_status(self) -> List[Dict[str, Any]]:
        """Returns catalog of models with local installation status and disk size."""
        status_list = []
        for m in WHISPER_MODELS:
            model_id = m["id"]
            # faster-whisper stores models under models--Systran--faster-whisper-{id} or direct folder
            is_installed = self.is_model_installed(model_id)
            size_on_disk = self._get_model_size_bytes(model_id)

            status_list.append({
                "id": model_id,
                "name": m["name"],
                "description": m["desc"],
                "size_mb": m["size_mb"],
                "installed": is_installed,
                "size_on_disk_bytes": size_on_disk,
                "size_on_disk_str": format_bytes(size_on_disk) if is_installed else "Not Downloaded"
            })
        return status_list

    def is_model_installed(self, model_id: str) -> bool:
        """Checks if model weights exist locally in the cache directory."""
        # 1. Check direct folder
        direct_dir = self.models_dir / model_id
        if direct_dir.exists() and any(direct_dir.iterdir()):
            return True

        # 2. Check HuggingFace hub cache structure
        hub_pattern = f"models--Systran--faster-whisper-{model_id}"
        hub_dir = self.models_dir / hub_pattern
        if hub_dir.exists() and (hub_dir / "snapshots").exists():
            snapshots = list((hub_dir / "snapshots").iterdir())
            if snapshots and any(snapshots[0].iterdir()):
                return True

        return False

    def _get_model_size_bytes(self, model_id: str) -> int:
        target_dirs = [
            self.models_dir / model_id,
            self.models_dir / f"models--Systran--faster-whisper-{model_id}"
        ]
        total_bytes = 0
        for td in target_dirs:
            if td.exists():
                for p in td.rglob("*"):
                    if p.is_file():
                        total_bytes += p.stat().st_size
        return total_bytes

    def download_model(
        self,
        model_id: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """Downloads faster-whisper model weights to local storage for offline use."""
        from faster_whisper import download_model

        logger.info(f"Downloading faster-whisper model: {model_id} to {self.models_dir}")
        if progress_callback:
            progress_callback(10.0, f"Starting download of model '{model_id}'...")

        try:
            downloaded_path = download_model(
                model_id,
                output_dir=str(self.models_dir / model_id)
            )
            if progress_callback:
                progress_callback(100.0, f"Model '{model_id}' downloaded and ready for offline use.")
            logger.info(f"Model {model_id} successfully cached at {downloaded_path}")
            return Path(downloaded_path)
        except Exception as e:
            logger.error(f"Failed to download model {model_id}: {e}")
            raise RuntimeError(f"Could not download model {model_id}: {e}")


model_manager = ModelManager()
