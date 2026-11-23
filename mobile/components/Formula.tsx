import { useState } from 'react';
import { View } from 'react-native';
import { Button, PressableFeedback } from 'heroui-native';
import { ChevronDown, ChevronUp } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { AppText } from './AppText';
import { DataState } from './DataState';
import { bandLabels, ratingColors } from './ScoreBadge';
import { router } from 'expo-router';
import { colors } from '@/lib/theme';
import type { Analysis, Ingredient } from '@/lib/api/types';
export function AnalysisScore({ analysis }: { analysis: Analysis }) {
  const matched = analysis.ingredients.filter((item) => item.matched).length;
  return (
    <View style={{ backgroundColor: colors.ink, borderRadius: 18, padding: 20, gap: 12 }}>
      <View style={{ flexDirection: 'row', gap: 12, alignItems: 'center' }}>
        <View style={{ flex: 1, gap: 6 }}>
          <AppText weight="medium" style={{ color: colors.white, fontSize: 16 }}>
            Ingredient score
          </AppText>
          <AppText style={{ color: colors.lavender, fontSize: 12 }}>
            {analysis.score === null
              ? 'Insufficient data'
              : analysis.score_is_estimated
                ? 'Estimated score'
                : 'Calculated score'}
          </AppText>
        </View>
        {analysis.score !== null && (
          <AppText weight="semibold" style={{ color: colors.white, fontSize: 32 }}>
            {analysis.score}
            <AppText style={{ color: colors.lavender, fontSize: 12 }}>/100</AppText>
          </AppText>
        )}
      </View>
      <AppText style={{ color: colors.lavender, fontSize: 12 }}>
        {matched} of {analysis.ingredients.length} ingredients recognized
      </AppText>
      {analysis.score !== null && (
        <AppText style={{ color: colors.lavender, fontSize: 12 }}>
          {bandLabels[analysis.score_band ?? 'unknown']}
        </AppText>
      )}
      <AppText style={{ color: colors.lavender, fontSize: 11, lineHeight: 17 }}>
        Unknown ingredients are not a sign of safety. These results are not medical advice.
      </AppText>
    </View>
  );
}
export function IngredientRow({
  ingredient,
  onChoose,
}: {
  ingredient: Ingredient;
  onChoose?: (ingredient: Ingredient) => void;
}) {
  const [open, setOpen] = useState(false);
  const palette = ratingColors[ingredient.matched ? ingredient.risk_level : 'unknown'];
  return (
    <View style={{ borderTopWidth: 1, borderTopColor: colors.border }}>
      <PressableFeedback
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
        accessibilityLabel={`${ingredient.name}, show explanation`}
        onPress={() => {
          setOpen(!open);
          void Haptics.selectionAsync();
        }}
        style={{ paddingVertical: 17 }}
      >
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <View style={{ flex: 1, gap: 5 }}>
            <AppText weight="semibold" style={{ fontSize: 14, color: palette.foreground }}>
              {ingredient.name}
            </AppText>
            {ingredient.inci_name &&
              ingredient.inci_name.toLowerCase() !== ingredient.name.toLowerCase() && (
                <AppText style={{ fontSize: 11, color: colors.muted }}>
                  {ingredient.inci_name}
                </AppText>
              )}
          </View>
          <AppText
            numberOfLines={1}
            style={{
              color: palette.foreground,
              backgroundColor: palette.background,
              padding: 6,
              borderRadius: 12,
              fontSize: 11,
            }}
          >
            {bandLabels[ingredient.matched ? ingredient.risk_level : 'unknown']}
          </AppText>
          {open ? (
            <ChevronUp size={16} color={colors.muted} strokeWidth={1.8} />
          ) : (
            <ChevronDown size={16} color={colors.muted} strokeWidth={1.8} />
          )}
        </View>
      </PressableFeedback>
      {open && (
        <View style={{ gap: 10, paddingBottom: 18 }}>
          <AppText style={{ fontSize: 13, lineHeight: 21, color: colors.muted }}>
            {ingredient.rationale ??
              ingredient.summary ??
              (ingredient.matched
                ? 'No explanation is available yet.'
                : 'This ingredient has not been recognized.')}
          </AppText>
          {ingredient.rating !== null && (
            <AppText style={{ fontSize: 11, color: colors.muted }}>
              Ingredient rating: {ingredient.rating}/10
            </AppText>
          )}
          {onChoose && ingredient.ingredient_id && (
            <Button size="sm" variant="secondary" onPress={() => onChoose(ingredient)}>
              <Button.Label>Add allergy or avoidance</Button.Label>
            </Button>
          )}
        </View>
      )}
    </View>
  );
}
export function Formula({
  analysis,
  onChoose,
  onEmpty,
}: {
  analysis: Analysis;
  onChoose?: (ingredient: Ingredient) => void;
  onEmpty?: () => void;
}) {
  return (
    <View style={{ gap: 18 }}>
      {!!analysis.summary && <AppText style={{ lineHeight: 22 }}>{analysis.summary}</AppText>}
      <AppText weight="semibold" style={{ fontSize: 20 }}>
        Inside the formula
      </AppText>
      {analysis.ingredients.length ? (
        analysis.ingredients.map((ingredient) => (
          <IngredientRow
            key={`${ingredient.position}-${ingredient.name}`}
            ingredient={ingredient}
            onChoose={onChoose}
          />
        ))
      ) : (
        <DataState
          message="No ingredient list is available."
          action="Read a label"
          onAction={onEmpty ?? (() => router.push('/analysis'))}
        />
      )}
    </View>
  );
}
