import { View } from 'react-native';
import { Star } from 'lucide-react-native';
import { AppText } from '@/components/AppText';
import type { Review } from '@/lib/api/types';
import { formatReviewDate } from '@/lib/reviews';
import { colors } from '@/lib/theme';

export function ReviewCard({ review }: { review: Review }) {
  const isApp = review.source === 'app';

  return (
    <View
      style={{
        backgroundColor: colors.white,
        borderRadius: 14,
        padding: 16,
        gap: 10,
        borderWidth: 1,
        borderColor: colors.border,
      }}
    >
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <View style={{ gap: 2, flex: 1 }}>
          <AppText weight="semibold" numberOfLines={1}>
            {review.author_name}
          </AppText>
          <AppText style={{ fontSize: 12, color: colors.muted }}>
            {formatReviewDate(review.created_at)}
          </AppText>
        </View>

        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: 5,
            paddingHorizontal: 8,
            paddingVertical: 3,
            borderRadius: isApp ? 6 : 999,
            backgroundColor: isApp ? colors.greenSoft : colors.orangeSoft,
          }}
        >
          <AppText
            weight="bold"
            style={{
              fontSize: 11,
              color: isApp ? colors.green : colors.orange,
            }}
          >
            {isApp ? 'A' : 'R'}
          </AppText>
          <AppText
            weight="medium"
            style={{
              fontSize: 11,
              color: isApp ? colors.green : colors.orange,
            }}
          >
            {isApp ? 'App' : 'Reddit'}
          </AppText>
        </View>
      </View>

      {review.rating !== null && (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}>
          {[1, 2, 3, 4, 5].map((starIndex) => (
            <Star
              key={starIndex}
              size={13}
              color={starIndex <= review.rating! ? colors.amber : colors.border}
              fill={starIndex <= review.rating! ? colors.amber : 'transparent'}
            />
          ))}
        </View>
      )}

      <AppText style={{ lineHeight: 21 }}>{review.body}</AppText>
    </View>
  );
}
