import { Linking, View } from 'react-native';
import { BadgeCheck, ExternalLink } from 'lucide-react-native';
import { Button } from 'heroui-native';
import { useTranslation } from 'react-i18next';
import { router } from 'expo-router';
import { AppText } from '@/components/AppText';
import { DataState, LoadingState } from '@/components/DataState';
import { LibraryProductRow } from '@/components/LibraryProductRow';
import { Screen } from '@/components/Screen';
import { useDermatologistGuidance } from '@/lib/api/queries';
import { colors } from '@/lib/theme';

export default function DermatologistGuidanceScreen() {
  const { t } = useTranslation();
  const result = useDermatologistGuidance();

  return (
    <Screen title={t('guidance.title')}>
      <AppText weight="semibold" style={{ fontSize: 27, lineHeight: 34 }}>
        {t('guidance.title')}
      </AppText>
      <AppText style={{ color: colors.muted, lineHeight: 21 }}>{t('guidance.subtitle')}</AppText>
      <AppText style={{ color: colors.muted, lineHeight: 21 }}>
        {t('guidance.informationOnly')}
      </AppText>
      {result.isPending ? (
        <LoadingState />
      ) : result.isError ? (
        <DataState
          error={result.error}
          onAction={() => {
            void result.refetch();
          }}
        />
      ) : result.data?.recommendations.length ? (
        <>
          {result.data.recommendations.map((recommendation) => (
            <View
              key={recommendation.id}
              style={{
                gap: 14,
                padding: 18,
                borderWidth: 1,
                borderColor: colors.border,
                borderRadius: 20,
              }}
            >
              <AppText weight="semibold" style={{ fontSize: 20, lineHeight: 27 }}>
                {recommendation.title}
              </AppText>
              {recommendation.dermatologist && (
                <View style={{ gap: 4 }}>
                  <AppText weight="medium">{recommendation.dermatologist.display_name}</AppText>
                  <AppText style={{ color: colors.muted }}>
                    {recommendation.dermatologist.credentials} ·{' '}
                    {recommendation.dermatologist.specialty}
                  </AppText>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                    <BadgeCheck
                      size={17}
                      color={recommendation.dermatologist.is_verified ? colors.green : colors.muted}
                      accessibilityLabel={
                        recommendation.dermatologist.is_verified
                          ? t('guidance.verified')
                          : t('guidance.notVerified')
                      }
                    />
                    <AppText style={{ color: colors.green, fontSize: 12 }}>
                      {recommendation.dermatologist.is_verified
                        ? t('guidance.verified')
                        : t('guidance.notVerified')}
                    </AppText>
                  </View>
                </View>
              )}
              <AppText style={{ lineHeight: 22 }}>{recommendation.advice}</AppText>
              <Button
                variant="tertiary"
                style={{ alignSelf: 'flex-start', minHeight: 44, paddingHorizontal: 0 }}
                accessibilityLabel={`${t('guidance.source')}: ${recommendation.source_title}`}
                onPress={() => void Linking.openURL(recommendation.source_url)}
              >
                <Button.Label>{t('guidance.source')}</Button.Label>
                <ExternalLink size={16} color={colors.ink} />
              </Button>
              {!!recommendation.related_products.length && (
                <View style={{ gap: 8 }}>
                  <AppText weight="semibold">{t('guidance.relatedProducts')}</AppText>
                  {recommendation.related_products.map((product) => (
                    <LibraryProductRow key={product.id} product={product} />
                  ))}
                </View>
              )}
            </View>
          ))}
          <AppText style={{ color: colors.muted, fontSize: 12, lineHeight: 19 }}>
            {result.data.disclaimer}
          </AppText>
        </>
      ) : (
        <DataState
          message={t('guidance.empty')}
          action={t('library.browse')}
          onAction={() => router.push('/')}
        />
      )}
    </Screen>
  );
}
