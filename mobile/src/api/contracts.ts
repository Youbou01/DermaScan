/** Frozen Sprint 2 mock DTOs. These are not live API types until OpenAPI exports them. */
export interface AuthUser {
  readonly id: string;
  readonly email: string;
  readonly display_name: string;
}

export interface AuthSession {
  readonly access_token: string;
  readonly refresh_token: string;
  readonly token_type: 'bearer';
  readonly user: AuthUser;
}

export interface ProfileDTO {
  readonly user_id: string;
  readonly skin_type: 'normal' | 'dry' | 'oily' | 'combination' | 'sensitive' | null;
  readonly is_pregnant_or_nursing: boolean;
  readonly health_conditions: readonly string[];
  readonly allergy_ingredient_ids: readonly string[];
  readonly blacklisted_product_ids: readonly string[];
}

export interface SuitabilityAlertDTO {
  readonly code: string;
  readonly severity: 'high' | 'moderate';
  readonly ingredient_name: string | null;
  readonly title: string;
  readonly detail: string;
}

export interface SuitabilityDTO {
  readonly product_id: string;
  readonly suits_profile: boolean;
  readonly verdict: 'suitable' | 'caution' | 'avoid';
  readonly has_risk_alert: boolean;
  readonly is_blacklisted: boolean;
  readonly alerts: readonly SuitabilityAlertDTO[];
}
