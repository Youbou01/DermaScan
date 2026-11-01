import { useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { suggestIngredients } from './ingredient-suggestions';

export interface IngredientChipsProps {
  title: string;
  names: string[];
  onAdd: (name: string) => void;
  onRemove: (name: string) => void;
}

export function IngredientChips({
  title,
  names,
  onAdd,
  onRemove,
}: IngredientChipsProps): ReactElement {
  const colors = useThemeColors();
  const { t } = useTranslation();
  const [text, setText] = useState('');
  const suggestions = suggestIngredients(text).filter(
    (suggestion) => !names.some((name) => name.toLowerCase() === suggestion.toLowerCase()),
  );

  function add(name: string): void {
    onAdd(name);
    setText('');
  }

  return (
    <View style={styles.block}>
      <Text style={[styles.label, { color: colors.text }]}>{title}</Text>
      <View style={styles.row}>
        {names.map((name) => (
          <Pressable
            accessibilityLabel={`${t('filters.remove')} ${name}`}
            accessibilityRole="button"
            key={name}
            onPress={() => onRemove(name)}
            style={[
              styles.chip,
              { borderColor: colors.primary, backgroundColor: colors.surfaceMuted },
            ]}
          >
            <Text style={[styles.chipText, { color: colors.text }]}>{`${name} ×`}</Text>
          </Pressable>
        ))}
      </View>
      <TextInput
        accessibilityLabel={title}
        autoCapitalize="none"
        autoCorrect={false}
        onChangeText={setText}
        onSubmitEditing={() => {
          if (suggestions[0]) add(suggestions[0]);
        }}
        placeholder={t('filters.ingredient_input')}
        placeholderTextColor={colors.textMuted}
        style={[
          styles.input,
          { color: colors.text, borderColor: colors.border, backgroundColor: colors.surface },
        ]}
        value={text}
      />
      <View style={styles.row}>
        {suggestions.map((suggestion) => (
          <Pressable
            accessibilityRole="button"
            key={suggestion}
            onPress={() => add(suggestion)}
            style={[styles.chip, { borderColor: colors.border, backgroundColor: colors.surface }]}
          >
            <Text style={[styles.chipText, { color: colors.text }]}>{suggestion}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  block: { gap: spacing.md },
  label: {
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    fontWeight: typography.weight.semibold,
  },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  chip: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.pill,
  },
  chipText: { fontSize: typography.size.md, lineHeight: typography.lineHeight.md },
  input: {
    minHeight: 44,
    paddingHorizontal: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.lg,
    fontSize: typography.size.md,
  },
});
