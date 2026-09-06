"""
Model weight downloader and cache manager for InsightFace models.
Manages downloading, verifying, caching, and fallback between buffalo_sc and buffalo_l.
"""

import os
import io
import time
import zipfile
import logging
import urllib.request
import urllib.error
import http.client
from pathlib import Path
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger("trace.ml.weights_loader")

BUFFALO_SC_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_sc.zip"
BUFFALO_L_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"

MODEL_URLS: Dict[str, str] = {
    "buffalo_sc": BUFFALO_SC_URL,
    "buffalo_l": BUFFALO_L_URL,
}

# Key ONNX files required for each model pack to be considered valid
REQUIRED_MODEL_FILES: Dict[str, List[str]] = {
    "buffalo_sc": ["det_500m.onnx", "w600k_mbf.onnx"],
    "buffalo_l": ["det_10g.onnx", "w600k_r50.onnx"],
}


def get_insightface_root(custom_root: Optional[str] = None) -> Path:
    """Return the base InsightFace directory (~/.insightface by default)."""
    if custom_root:
        return Path(os.path.expanduser(custom_root)).resolve()
    env_root = os.environ.get("INSIGHTFACE_ROOT")
    if env_root:
        return Path(os.path.expanduser(env_root)).resolve()
    return Path(os.path.expanduser("~/.insightface")).resolve()


def get_model_dir(model_name: str = "buffalo_sc", root_dir: Optional[str] = None) -> Path:
    """Return the directory path for the given model pack."""
    base = get_insightface_root(root_dir)
    return base / "models" / model_name


def is_model_cached(model_name: str = "buffalo_sc", root_dir: Optional[str] = None) -> bool:
    """
    Check if the specified model pack is already downloaded and contains required ONNX models.
    """
    model_dir = get_model_dir(model_name, root_dir)
    if not model_dir.is_dir():
        return False
    required_files = REQUIRED_MODEL_FILES.get(model_name, [])
    for fname in required_files:
        target = model_dir / fname
        if not target.is_file() or target.stat().st_size == 0:
            return False
    return True


def download_and_extract_model(
    model_name: str = "buffalo_sc",
    root_dir: Optional[str] = None,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    timeout: float = 60.0,
) -> Path:
    """
    Download and extract model weights from official release if not already cached.
    
    Args:
        model_name: "buffalo_sc" (default, ~14.2 MB) or "buffalo_l" (~288.6 MB).
        root_dir: Base directory (defaults to ~/.insightface).
        max_retries: Number of download retry attempts.
        retry_delay: Delay in seconds between retries.
        timeout: HTTP request timeout.
        
    Returns:
        Path to extracted model directory.
    """
    target_dir = get_model_dir(model_name, root_dir)
    if is_model_cached(model_name, root_dir):
        logger.info("Model '%s' is already cached at: %s", model_name, target_dir)
        return target_dir

    if model_name not in MODEL_URLS:
        raise ValueError(
            f"Unsupported model '{model_name}'. Supported models: {list(MODEL_URLS.keys())}"
        )

    download_url = MODEL_URLS[model_name]
    target_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading '%s' from %s ...", model_name, download_url)

    last_error: Optional[Exception] = None
    headers = {"User-Agent": "TRACE-ML-Engine/1.0 (macOS/Darwin)"}

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(download_url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content_len = response.headers.get("Content-Length")
                total_bytes = int(content_len) if content_len else None
                logger.info(
                    "Download attempt %d/%d for '%s' (size: %s bytes)",
                    attempt,
                    max_retries,
                    model_name,
                    total_bytes or "unknown",
                )

                zip_buffer = io.BytesIO()
                chunk_size = 64 * 1024
                downloaded = 0
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    zip_buffer.write(chunk)
                    downloaded += len(chunk)

                zip_buffer.seek(0)
                with zipfile.ZipFile(zip_buffer) as zf:
                    zf.extractall(target_dir)

            if is_model_cached(model_name, root_dir):
                logger.info(
                    "Successfully downloaded and verified '%s' at: %s",
                    model_name,
                    target_dir,
                )
                return target_dir
            else:
                raise RuntimeError(
                    f"Model extraction completed but required files missing in {target_dir}"
                )

        except (urllib.error.URLError, http.client.HTTPException, zipfile.BadZipFile, RuntimeError, OSError) as exc:
            last_error = exc
            logger.warning(
                "Attempt %d/%d failed for '%s': %s",
                attempt,
                max_retries,
                model_name,
                exc,
            )
            if attempt < max_retries:
                time.sleep(retry_delay * attempt)

    raise RuntimeError(
        f"Failed to download and extract model '{model_name}' after {max_retries} attempts: {last_error}"
    )


def ensure_model_available(
    primary_model: str = "buffalo_sc",
    fallback_model: Optional[str] = "buffalo_l",
    root_dir: Optional[str] = None,
) -> Tuple[str, Path]:
    """
    Ensure a valid InsightFace model pack is present.
    Attempts primary_model first; if downloading fails, attempts fallback_model.
    
    Returns:
        Tuple of (active_model_name, model_dir_path).
    """
    # 1. Fast check if primary is already cached
    if is_model_cached(primary_model, root_dir):
        return primary_model, get_model_dir(primary_model, root_dir)

    # 2. Check if fallback is already cached
    if fallback_model and is_model_cached(fallback_model, root_dir):
        logger.info(
            "Primary '%s' not cached, but fallback '%s' already cached.",
            primary_model,
            fallback_model,
        )
        return fallback_model, get_model_dir(fallback_model, root_dir)

    # 3. Attempt downloading primary
    try:
        path = download_and_extract_model(primary_model, root_dir=root_dir)
        return primary_model, path
    except Exception as primary_err:
        logger.warning(
            "Failed downloading primary model '%s' (%s). Trying fallback '%s'...",
            primary_model,
            primary_err,
            fallback_model,
        )
        if fallback_model and fallback_model != primary_model:
            try:
                path = download_and_extract_model(fallback_model, root_dir=root_dir)
                return fallback_model, path
            except Exception as fb_err:
                raise RuntimeError(
                    f"Both primary '{primary_model}' and fallback '{fallback_model}' failed to load: {fb_err}"
                ) from fb_err
        raise primary_err
