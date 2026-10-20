import type { components } from './generated/schema';

type ProblemDetails = components['schemas']['ProblemDetails'];
type ValidationErrors = NonNullable<ProblemDetails['errors']>;

interface ProblemLike {
  readonly type?: unknown;
  readonly title?: unknown;
  readonly status?: unknown;
  readonly detail?: unknown;
  readonly instance?: unknown;
  readonly request_id?: unknown;
  readonly errors?: unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function readString(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

function readErrors(value: unknown): ValidationErrors | null {
  return Array.isArray(value) && value.every(isRecord) ? (value as ValidationErrors) : null;
}

export class ApiError extends Error {
  readonly type: string;
  readonly title: string;
  readonly status: number;
  readonly detail: string | null;
  readonly instance: string | null;
  readonly request_id: string | null;
  readonly errors: ValidationErrors | null;

  constructor(status: number, problem: ProblemLike = {}, requestId: string | null = null) {
    const title = readString(problem.title) ?? 'Request failed';
    const detail = readString(problem.detail);
    super(detail ? `${title}: ${detail}` : title);
    this.name = 'ApiError';
    this.type = readString(problem.type) ?? 'about:blank';
    this.title = title;
    this.status = status;
    this.detail = detail;
    this.instance = readString(problem.instance);
    this.request_id = readString(problem.request_id) ?? requestId;
    this.errors = readErrors(problem.errors);
  }

  static async fromResponse(response: Response, parsedBody?: unknown): Promise<ApiError> {
    const contentType = response.headers.get('content-type')?.toLowerCase() ?? '';
    let body: unknown;
    if (contentType.includes('application/problem+json')) {
      if (parsedBody !== undefined) {
        body = parsedBody;
      } else {
        try {
          body = await response.json();
        } catch {
          body = undefined;
        }
      }
    }
    return new ApiError(
      response.status,
      isRecord(body) ? body : {},
      response.headers.get('x-request-id'),
    );
  }
}
