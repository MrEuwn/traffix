"""Camera and YOLO routes: readiness, recorded-frame replay, and YOLO inference."""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.services.camera_service import camera_service
from app.services.frame_service import frame_service
from core.responses import success_response
from core.schemas import StandardSuccessResponse

router = APIRouter(
    prefix="/cameras",
    tags=["Cameras / YOLO"],
)


@router.get(
    "/status",
    response_model=StandardSuccessResponse,
    summary="Camera and YOLO Status",
    description="Returns readiness metadata for camera input and YOLO integration.",
)
async def camera_status(request: Request) -> StandardSuccessResponse:
    """Return camera and YOLO status.

    Args:
        request: Incoming FastAPI request.

    Returns:
        Standardized camera status response.
    """
    return success_response(
        message="Camera and YOLO status retrieved",
        data=camera_service.status(),
        request_id=request.state.request_id,
    )


@router.get(
    "",
    response_model=StandardSuccessResponse,
    summary="List Camera Slots",
    description="Returns camera slots mapped to simulated intersections.",
)
async def list_cameras(request: Request) -> StandardSuccessResponse:
    """Return configured camera slots.

    Args:
        request: Incoming FastAPI request.

    Returns:
        Standardized camera list response.
    """
    cameras = camera_service.list_cameras()
    return success_response(
        message="Camera slots retrieved",
        data={"count": len(cameras), "cameras": cameras},
        request_id=request.state.request_id,
    )


@router.get(
    "/videos/{period}/{filename}",
    summary="Get Camera Video",
    description="Serves a recorded CCTV video from backend-managed storage.",
)
def get_camera_video(period: str, filename: str) -> FileResponse:
    """Return a recorded CCTV video file, fetching it from Drive if needed.

    Defined as a sync function so FastAPI runs it in a worker thread,
    keeping the blocking Drive download off the main event loop.
    """
    video_path = camera_service.resolve_video_path_with_drive_fetch(period, filename)
    if video_path is None:
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=filename,
    )


@router.get(
    "/frames",
    response_model=StandardSuccessResponse,
    summary="Recorded CCTV frames with YOLO detections",
    description="Catalogue of replayed public CCTV frames and the stored YOLOv8 detections for each.",
)
async def list_frames(request: Request) -> StandardSuccessResponse:
    """Return the frame catalogue (boxes included) or `available: false`."""
    catalogue = frame_service.catalogue()
    live_ok, live_reason = frame_service.live_available()
    if catalogue is None:
        data = {
            "available": False,
            "reason": "detections.json belum ada — jalankan python backend/scripts/run_yolo_frames.py",
        }
    else:
        data = {
            "available": True,
            "mode": "precomputed",
            "source": catalogue["source"],
            "model": catalogue["model"],
            "caveats": catalogue["caveats"],
            "summary": catalogue["summary"],
            "generated_at": catalogue["generated_at"],
            "frames": catalogue["frames"],
        }
    data["live_inference_available"] = live_ok
    data["live_inference_reason"] = live_reason
    return success_response(
        message="Recorded frames retrieved",
        data=data,
        request_id=request.state.request_id,
    )


@router.get(
    "/frames/{frame_id}/image",
    summary="Recorded CCTV frame image",
    description="JPEG of a recorded frame, with YOLO boxes drawn (`annotated=true`) or raw.",
)
def get_frame_image(frame_id: str, annotated: bool = Query(default=True)) -> FileResponse:
    """Serve a catalogued frame; ids not in the catalogue are 404.

    `annotated=true` asks for the rendered version with boxes. If that render is not on
    disk (the folder is gitignored and only rebuilt by run_yolo_frames.py), the raw frame
    is served and `X-Frame-Variant: source` says so, instead of failing with 404.
    """
    path, variant = frame_service.image(frame_id, annotated)
    if path is None:
        raise HTTPException(status_code=404, detail="Frame not found")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600", "X-Frame-Variant": variant or ""},
    )


@router.post(
    "/frames/{frame_id}/infer",
    response_model=StandardSuccessResponse,
    summary="Run YOLO now on a recorded frame",
    description="Executes the trained YOLOv8 weights on the frame and returns fresh boxes and timing.",
)
def infer_frame(
    request: Request,
    frame_id: str,
    conf: float = Query(default=0.25, ge=0.05, le=0.95),
) -> StandardSuccessResponse:
    """Live inference on replayed footage; 503 when the runtime lacks ultralytics."""
    try:
        result = frame_service.infer(frame_id, conf=conf)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Frame not found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return success_response(
        message="YOLO inference completed",
        data=result,
        request_id=request.state.request_id,
    )
