from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette import status


class AppError(Exception):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Request validation failed", "errors": exc.errors()},
    )


async def integrity_error_handler(_: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "The request conflicts with existing data"},
    )