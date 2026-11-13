import createClient from 'openapi-fetch';
import { env } from '@/config/env';
import { getActiveAccessToken } from './auth-token';
import { getActiveApiLocale } from './locale';
import { categoriesFixture, homeFixture, productCardsFixture, productFixture } from './fixtures';
import { findMockSearchResults } from './search-fixture';
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
  if (url.pathname === '/api/v1/products/search') {
    const q = url.searchParams.get('q') ?? '';
    return mockResponse(findMockSearchResults(q));
  }
  if (url.pathname === '/api/v1/products/filter') {
    const category = url.searchParams.get('category');
    const band = url.searchParams.get('band');
    const minScoreRaw = url.searchParams.get('min_score');
    const minScore = minScoreRaw ? Number(minScoreRaw) : null;
    const filtered = productCardsFixture.filter((item) => {
      if (category && item.category_slug !== category) return false;
      if (band && item.score_band !== band) return false;
      if (minScore !== null && (item.score === null || item.score < minScore)) return false;
      return true;
    });
    return mockResponse({
      items: filtered.map((item) => ({
        ...item,
        barcode: '6190000000019',
        score_band: item.score_band ?? 'unknown',
      })),
      next_cursor: null,
    });
  }
  const barcode = url.pathname.match(/^\/api\/v1\/products\/by-barcode\/([^/]+)$/)?.[1];
  if (barcode !== undefined) {
    return barcode === productFixture.barcode
      ? mockResponse(productFixture)
      : mockProblemResponse('product-not-found', 'Product not found', 404);
  }
  const productId = url.pathname.match(/^\/api\/v1\/products\/([^/]+)$/)?.[1];
  if (productId !== undefined) {
    if (productId === productFixture.id) {
      return mockResponse(productFixture);
    }
    const cardMatch = productCardsFixture.find((c) => c.id === productId);
    if (cardMatch) {
      return mockResponse({
        ...productFixture,
        id: cardMatch.id,
        name: cardMatch.name,
        brand: cardMatch.brand,
        score: cardMatch.score,
        score_band: cardMatch.score_band ?? 'unknown',
        category: cardMatch.category_slug
          ? { slug: cardMatch.category_slug, name: cardMatch.category_slug }
          : null,
      });
    }
    return mockProblemResponse('product-not-found', 'Product not found', 404);
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
      const token = getActiveAccessToken();
      if (token) {
        request.headers.set('Authorization', `Bearer ${token}`);
      }
      return request;
    },
  });
  return client;
}

export const apiClient = createApiClient();
