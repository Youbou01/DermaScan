import { View } from 'react-native';
import { Star } from 'lucide-react-native';
import { AppText } from '@/components/AppText';
import { colors } from '@/lib/theme';

type Props = {
  avgRating: number | null;
  reviewCount: number;
};

export function RatingSummary({ avgRating, reviewCount }: Props) {
  if (reviewCount === 0 || avgRating === null) {
    return (
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 2 }}>
        <AppText style={{ color: colors.muted, fontSize: 13 }}>No reviews yet</AppText>
      </View>
    );
  }

  const rounded = Math.round(avgRating);

  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 4 }}>
      <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 2 }}>
        <AppText weight="bold" style={{ fontSize: 16, color: colors.ink }}>
          {avgRating.toFixed(1)}
        </AppText>
        <AppText style={{ fontSize: 13, color: colors.muted }}>/ 5</AppText>
      </View>

      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 2 }}>
        {[1, 2, 3, 4, 5].map((starIndex) => (
          <Star
            key={starIndex}
            size={14}
            color={starIndex <= rounded ? colors.amber : colors.border}
            fill={starIndex <= rounded ? colors.amber : 'transparent'}
          />
        ))}
      </View>

      <AppText style={{ fontSize: 13, color: colors.muted }}>
        ({reviewCount} {reviewCount === 1 ? 'review' : 'reviews'})
      </AppText>
    </View>
  );
}
