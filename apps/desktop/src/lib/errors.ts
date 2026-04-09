export function toErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export async function readErrorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: { message?: string } | string };
    if (typeof body.detail === 'string') {
      return body.detail;
    }
    if (body.detail && typeof body.detail.message === 'string') {
      return body.detail.message;
    }
  } catch {
    return fallback;
  }
  return fallback;
}
