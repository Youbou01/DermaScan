import type {
  CategoryNode,
  HomeFeed,
  ProductCard,
  ProductDetail,
  ProductIngredient,
} from './types';

const categoriesEn: CategoryNode[] = [
  {
    slug: 'face-care',
    name: 'Face care',
    children: [
      { slug: 'cleanser', name: 'Cleanser', children: [] },
      { slug: 'serum', name: 'Serum', children: [] },
      { slug: 'moisturizer', name: 'Moisturizer', children: [] },
    ],
  },
  {
    slug: 'sun-care',
    name: 'Sun care',
    children: [{ slug: 'sunscreen', name: 'Sunscreen', children: [] }],
  },
];

const categoriesFr: CategoryNode[] = [
  {
    slug: 'face-care',
    name: 'Soin du visage',
    children: [
      { slug: 'cleanser', name: 'Nettoyant', children: [] },
      { slug: 'serum', name: 'Sérum', children: [] },
      { slug: 'moisturizer', name: 'Hydratant', children: [] },
    ],
  },
  {
    slug: 'sun-care',
    name: 'Protection solaire',
    children: [{ slug: 'sunscreen', name: 'Écran solaire', children: [] }],
  },
];

const serumProduct: ProductCard = {
  id: '0194f024-6c67-7e21-9e16-a774b0d53310',
  name: 'Daily Hydration Serum',
  brand: 'DermaScan Demo',
  image_url: null,
  score: 84,
  score_band: 'low',
  category_slug: 'serum',
};

const cleanserProduct: ProductCard = {
  id: '0194f024-6c67-7e21-9e16-a774b0d53311',
  name: 'Gentle Cream Cleanser',
  brand: 'DermaScan Demo',
  image_url: null,
  score: 68,
  score_band: 'moderate',
  category_slug: 'cleanser',
};

const products: ProductCard[] = [serumProduct, cleanserProduct];

const productIngredients: ProductIngredient[] = [
  {
    position: 1,
    name: 'Aqua',
    inci_name: 'Water',
    matched: true,
    risk_level: 'low',
    rationale: 'Commonly used as a solvent in cosmetic products.',
  },
  {
    position: 2,
    name: 'Glycerin',
    inci_name: 'Glycerin',
    matched: true,
    risk_level: 'low',
    rationale: 'A humectant used to help retain moisture.',
  },
  {
    position: 3,
    name: 'Parfum',
    inci_name: null,
    matched: false,
    risk_level: 'unknown',
    rationale: null,
  },
];

export const productFixture: ProductDetail = {
  id: serumProduct.id,
  barcode: '6190000000019',
  name: serumProduct.name,
  brand: serumProduct.brand,
  image_url: null,
  category: { slug: 'serum', name: 'Serum' },
  score: 84,
  score_band: 'low',
  score_coverage: 0.8,
  ingredients: productIngredients,
};

export const ingredientFixture = productIngredients;
export const categoriesFixture = { en: categoriesEn, fr: categoriesFr };

function homeFeed(locale: 'en' | 'fr'): HomeFeed {
  const categories = categoriesFixture[locale].map(({ slug, name }) => ({ slug, name }));
  const titles =
    locale === 'fr'
      ? { categories: 'Catégories', rated: 'Mieux notés', recent: 'Ajoutés récemment' }
      : { categories: 'Categories', rated: 'Top rated', recent: 'Recently added' };
  return {
    sections: [
      {
        id: 'categories',
        type: 'category_grid',
        title: titles.categories,
        items: categories,
        next_cursor: null,
      },
      {
        id: 'top_rated',
        type: 'top_rated',
        title: titles.rated,
        items: [serumProduct],
        next_cursor: null,
      },
      {
        id: 'recently_added',
        type: 'recently_added',
        title: titles.recent,
        items: products,
        next_cursor: null,
      },
    ],
  };
}

export const homeFixture = { en: homeFeed('en'), fr: homeFeed('fr') };
export const productCardsFixture = products;
