class AppError(Exception):
    pass


class NotFoundError(AppError):
    pass


class BadRequestError(AppError):
    pass


class ProcessingError(AppError):
    pass
