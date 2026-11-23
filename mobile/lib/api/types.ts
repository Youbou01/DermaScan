export type RiskBand = 'low' | 'moderate' | 'high' | 'unknown';
export type Product = {
  id: string;
  name: string;
  brand: string | null;
  image_url: string | null;
  barcode?: string;
  category_slug?: string | null;
  score: number | null;
  score_band: RiskBand | null;
  score_is_estimated?: boolean;
};
export type Category = { slug: string; name: string; children?: Category[] };
export type Ingredient = {
  position: number;
  name: string;
  inci_name: string | null;
  ingredient_id: string | null;
  matched: boolean;
  risk_level: RiskBand;
  rationale: string | null;
  rating: number | null;
  summary: string | null;
  confidence: number | null;
};
export type Analysis = {
  score: number | null;
  score_band: RiskBand | null;
  score_coverage: number;
  score_is_estimated: boolean;
  summary: string | null;
  ingredients: Ingredient[];
  extracted_text?: string;
};
export type ProductDetail = Product & Analysis & { category: Category | null; barcode: string };
export type Page<T> = { items: T[]; next_cursor: string | null };
export type HomeSection = Page<Product> & { id: string; type: string; title: string };
export type HomeFeed = {
  sections: Array<Omit<HomeSection, 'items'> & { items: Array<Product | Category> }>;
};
export type User = { id: string; email: string; display_name: string };
export type Session = { access_token: string; refresh_token: string; user: User };
export const skinTypes = ['normal', 'dry', 'oily', 'combination', 'sensitive'] as const;
export type SkinType = (typeof skinTypes)[number];
export const conditions = ['eczema', 'rosacea', 'acne_prone', 'psoriasis'] as const;
export type HealthCondition = (typeof conditions)[number];
export type ProfileInput = {
  skin_type: SkinType | null;
  is_pregnant_or_nursing: boolean;
  health_conditions: HealthCondition[];
  allergy_ingredient_ids: string[];
};
export type Profile = ProfileInput & { user_id: string; blacklisted_product_ids: string[] };
export type Blacklist = { product_ids: string[]; ingredient_ids: string[] };
export type Suitability = {
  product_id: string;
  suits_profile: boolean;
  verdict: 'suitable' | 'caution' | 'avoid';
  has_risk_alert: boolean;
  is_blacklisted: boolean;
  alerts: Array<{
    code: string;
    severity: 'high' | 'medium';
    ingredient_name: string;
    title: string;
    detail: string;
  }>;
};
export type Slot = 'morning' | 'evening';
export const stepTypes = [
  'cleanser',
  'toner',
  'serum',
  'moisturizer',
  'sunscreen',
  'treatment',
] as const;
export type StepType = (typeof stepTypes)[number];
export type StepInput = {
  step_order: number;
  step_type: StepType;
  product_id: string;
  notes: string | null;
};
export type RoutineStep = {
  id: string | null;
  step_order: number;
  step_type: StepType;
  product: Product;
  active_ingredients: string[];
  notes: string | null;
};
export type Conflict = {
  code: string;
  severity: 'high' | 'moderate';
  product_a_id: string;
  product_b_id: string;
  product_a_name: string;
  product_b_name: string;
  ingredient_a: string;
  ingredient_b: string;
  title: string;
  detail: string;
  resolution: string;
};
export type Routine = {
  id: string;
  slot: Slot;
  name: string;
  completed_today: boolean;
  steps: RoutineStep[];
  conflicts: Conflict[];
};
export type Recommendations = { skin_type: string; morning: RoutineStep[]; evening: RoutineStep[] };
export type Filters = {
  q?: string;
  category?: string;
  band?: RiskBand;
  min_score?: number;
  max_score?: number;
  include?: string[];
  exclude?: string[];
};
export type Contribution = { id: string; barcode: string; status: string; message: string };
