import createClient from 'openapi-fetch';
import { env } from '@/config/env';
import { getActiveApiLocale } from './locale';
import { categoriesFixture, homeFixture, productFixture } from './fixtures';
import type { paths } from './generated/schema';

function mockResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json',
      'content-language': getActiveApiLocale(),
      'x-request-id': 'mock-request-0001',
    },
  });
}

export const mockApiFetch: typeof fetch = async (input, _init): Promise<Response> => {
  const url = new URL(
    typeof input === 'string' ? input : input instanceof URL ? input.href : input.url,
  );
  const locale = getActiveApiLocale();
  if (url.pathname === '/api/v1/categories') {
    return mockResponse(categoriesFixture[locale]);
  }
  if (url.pathname === '/api/v1/home') {
    return mockResponse(homeFixture[locale]);
  }
  const barcode = url.pathname.match(/^\/api\/v1\/products\/by-barcode\/([^/]+)$/)?.[1];
  if (barcode !== undefined) {
    return barcode === productFixture.barcode
      ? mockResponse(productFixture)
      : mockProblemResponse('product-not-found', 'Product not found', 404);
  }
  const productId = url.pathname.match(/^\/api\/v1\/products\/([^/]+)$/)?.[1];
  if (productId !== undefined) {
    return productId === productFixture.id
      ? mockResponse(productFixture)
      : mockProblemResponse('product-not-found', 'Product not found', 404);
  }
  return mockProblemResponse(
    'mock-endpoint-not-found',
    `No mock fixture is registered for ${url.pathname}.`,
    404,
  );
};

function mockProblemResponse(code: string, title: string, status: number): Response {
  return new Response(
    JSON.stringify({
      type: `urn:skincare:problem:${code}`,
      title,
      status,
      request_id: 'mock-request-0001',
    }),
    {
      status,
      headers: {
        'content-type': 'application/problem+json',
        'x-request-id': 'mock-request-0001',
      },
    },
  );
}

export function createApiClient(
  fetchAdapter: typeof fetch = env.useMocks ? mockApiFetch : fetch,
): ReturnType<typeof createClient<paths>> {
  const client = createClient<paths>({ baseUrl: env.apiUrl, fetch: fetchAdapter });
  client.use({
    onRequest({ request }) {
      request.headers.set('Accept-Language', getActiveApiLocale());
      return request;
    },
  });
  return client;
}

export const apiClient = createApiClient();
