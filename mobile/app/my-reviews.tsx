import { PressableFeedback } from 'heroui-native';
import { View } from 'react-native';
import { Star } from 'lucide-react-native';
import { router } from 'expo-router';
import { ScreenList } from '@/components/ScreenList';
import { Screen } from '@/components/Screen';
import { AppText } from '@/components/AppText';
import { DataState, LoadingState, SignInGate } from '@/components/DataState';
import { useMyReviews, useUserId } from '@/lib/api/queries';
import type { UserReviewHistoryItem } from '@/lib/api/types';
import { formatReviewDate } from '@/lib/reviews';
import { colors } from '@/lib/theme';

export default function MyReviewsScreen() {
  const uid = useUserId();
  const reviews = useMyReviews();

  if (!uid) {
    return (
      <Screen title="My reviews">
        <SignInGate message="Sign in to view your reviewed products." />
      </Screen>
    );
  }

  const items = reviews.data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <ScreenList<UserReviewHistoryItem>
      title="My reviews"
      data={items}
      keyExtractor={(item) => item.id}
      ItemSeparatorComponent={() => <View style={{ height: 14 }} />}
      refreshing={reviews.isRefetching && !reviews.isFetchingNextPage}
      onRefresh={() => {
        void reviews.refetch();
      }}
      onEndReached={() => {
        if (reviews.hasNextPage && !reviews.isFetchingNextPage) {
          void reviews.fetchNextPage();
        }
      }}
      onEndReachedThreshold={0.4}
      ListEmptyComponent={
        reviews.isPending ? (
          <LoadingState />
        ) : reviews.isError ? (
          <DataState
            error={reviews.error}
            onAction={() => {
              void reviews.refetch();
            }}
          />
        ) : (
          <DataState
            message="You have not reviewed any products yet."
            action="Explore products"
            onAction={() => router.push('/')}
          />
        )
      }
      renderItem={({ item }) => (
        <PressableFeedback
          accessibilityRole="button"
          accessibilityLabel={`View ${item.product_name}`}
          onPress={() =>
            router.push({ pathname: '/product/[id]', params: { id: item.product_id } })
          }
          style={{
            backgroundColor: colors.white,
            borderRadius: 14,
            padding: 16,
            gap: 10,
            borderWidth: 1,
            borderColor: colors.border,
          }}
        >
          <View style={{ gap: 2 }}>
            {!!item.product_brand && (
              <AppText
                weight="semibold"
                numberOfLines={1}
                style={{ fontSize: 12, color: colors.muted }}
              >
                {item.product_brand}
              </AppText>
            )}
            <AppText weight="semibold" numberOfLines={2} style={{ fontSize: 16 }}>
              {item.product_name}
            </AppText>
          </View>

          {item.rating !== null && (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}>
              {[1, 2, 3, 4, 5].map((starIndex) => (
                <Star
                  key={starIndex}
                  size={14}
                  color={starIndex <= item.rating! ? colors.amber : colors.border}
                  fill={starIndex <= item.rating! ? colors.amber : 'transparent'}
                />
              ))}
            </View>
          )}

          <AppText style={{ lineHeight: 21 }}>{item.body}</AppText>

          <AppText style={{ fontSize: 12, color: colors.muted }}>
            Reviewed on {formatReviewDate(item.created_at)}
          </AppText>
        </PressableFeedback>
      )}
    />
  );
}
