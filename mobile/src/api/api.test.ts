import { ApiError } from './errors';
import { createApiClient, mockApiFetch } from './client';
import { categoriesFixture, homeFixture, ingredientFixture, productFixture } from './fixtures';
import { getActiveApiLocale, setApiLocale } from './locale';
import { searchFixture } from './search-fixture';
import i18n from '@/i18n/i18n';

describe('API layer', () => {
  beforeEach(() => {
    setApiLocale('en');
  });

  it('sends the active locale on every request', async () => {
    const requests: Request[] = [];
    const fetchAdapter: typeof fetch = async (input, init) => {
      requests.push(new Request(input, init));
      return new Response(JSON.stringify(categoriesFixture.fr), {
        headers: { 'content-type': 'application/json' },
      });
    };
    setApiLocale('fr-TN');

    const client = createApiClient(fetchAdapter);
    const result = await client.GET('/api/v1/categories');

    expect(result.data?.[0]?.name).toBe('Soin du visage');
    expect(requests).toHaveLength(1);
    expect(requests[0]?.headers.get('Accept-Language')).toBe('fr');
    expect(getActiveApiLocale()).toBe('fr');
  });

  it('parses RFC problem details and validation errors', async () => {
    const response = new Response(
      JSON.stringify({
        type: 'urn:skincare:problem:request-validation-failed',
        title: 'Request validation failed',
        status: 422,
        detail: 'The limit is outside the permitted range.',
        instance: '/api/v1/home',
        errors: [
          { loc: ['query', 'limit'], msg: 'Input should be less than 50', type: 'less_than' },
        ],
      }),
      {
        status: 422,
        headers: {
          'content-type': 'application/problem+json',
          'x-request-id': 'trace-12345678',
        },
      },
    );

    const error = await ApiError.fromResponse(response);

    expect(error).toMatchObject({
      name: 'ApiError',
      type: 'urn:skincare:problem:request-validation-failed',
      title: 'Request validation failed',
      status: 422,
      detail: 'The limit is outside the permitted range.',
      instance: '/api/v1/home',
      request_id: 'trace-12345678',
      errors: [{ loc: ['query', 'limit'], msg: 'Input should be less than 50', type: 'less_than' }],
    });
    expect(error.message).toBe(
      'Request validation failed: The limit is outside the permitted range.',
    );
  });

  it.each([
    [502, 'text/html', '<html>upstream unavailable</html>'],
    [500, 'application/json', '{"message":"unexpected server response"}'],
  ])('falls back safely for unformatted %s responses', async (status, contentType, body) => {
    const response = new Response(body, {
      status,
      headers: { 'content-type': contentType, 'x-request-id': 'trace-fallback-1' },
    });

    const error = await ApiError.fromResponse(response);

    expect(error).toMatchObject({
      name: 'ApiError',
      type: 'about:blank',
      title: i18n.t('errors.request_failed'),
      status,
      detail: null,
      request_id: 'trace-fallback-1',
      errors: null,
    });
    expect(error.message).toBe(i18n.t('errors.request_failed'));
  });

  it('serves localized mock responses for the published API domains', async () => {
    setApiLocale('fr');

    const categoriesResponse = await mockApiFetch(
      'https://mock.invalid/api/v1/categories',
      undefined,
    );
    const homeResponse = await mockApiFetch('https://mock.invalid/api/v1/home', undefined);
    const productResponse = await mockApiFetch(
      'https://mock.invalid/api/v1/products/by-barcode/6190000000019',
      undefined,
    );
    const categories = await categoriesResponse.json();
    const home = await homeResponse.json();
    const product = await productResponse.json();

    expect(categories).toEqual(categoriesFixture.fr);
    expect(home).toEqual(homeFixture.fr);
    expect(product).toEqual(productFixture);
    expect(productFixture.ingredients).toEqual(ingredientFixture);
    expect(homeResponse.headers.get('content-language')).toBe('fr');
  });

  it('keeps the documented proposed search result fixture complete', () => {
    expect(searchFixture).toMatchObject({
      items: expect.arrayContaining([
        expect.objectContaining({
          id: expect.any(String),
          name: expect.any(String),
          score: expect.any(Number),
          score_band: 'low',
        }),
      ]),
      next_cursor: null,
    });
  });
});
