export interface APIErrorBody {
  code: string;
  details: null | Record<string, unknown> | ValidationErrorItem[];
  message: string;
}

export interface ValidationErrorItem {
  field: string;
  message: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isValidationErrorItem(value: unknown): value is ValidationErrorItem {
  return (
    isRecord(value) &&
    typeof value.field === 'string' &&
    typeof value.message === 'string'
  );
}

export function parseAPIError(value: unknown): APIErrorBody | null {
  if (!isRecord(value)) {
    return null;
  }

  const response = isRecord(value.response) ? value.response : null;
  const data = response && isRecord(response.data) ? response.data : value;
  const error = isRecord(data.error) ? data.error : null;

  if (
    !error ||
    typeof error.code !== 'string' ||
    typeof error.message !== 'string'
  ) {
    return null;
  }

  let details: APIErrorBody['details'] = null;
  if (Array.isArray(error.details)) {
    details = error.details.every(isValidationErrorItem) ? error.details : null;
  } else if (isRecord(error.details)) {
    details = error.details;
  }

  return {
    code: error.code,
    details,
    message: error.message,
  };
}
