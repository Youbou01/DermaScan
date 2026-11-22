import { View } from 'react-native';
import { Button } from 'heroui-native';
import { router } from 'expo-router';
import { Screen } from '@/components/Screen';
import { AppText } from '@/components/AppText';
import { DataState, LoadingState } from '@/components/DataState';
import { useCategories } from '@/lib/api/queries';
import type { Category } from '@/lib/api/types';
function CategoryRow({ item, depth = 0 }: { item: Category; depth?: number }) {
  return (
    <View style={{ gap: 8, paddingLeft: depth ? 14 : 0 }}>
      <Button
        variant="tertiary"
        style={{ justifyContent: 'flex-start' }}
        onPress={() => router.push({ pathname: '/', params: { category: item.slug } })}
      >
        <Button.Label numberOfLines={1}>{item.name}</Button.Label>
      </Button>
      {item.children?.map((child) => (
        <CategoryRow key={child.slug} item={child} depth={depth + 1} />
      ))}
    </View>
  );
}
export default function CategoriesScreen() {
  const result = useCategories();
  return (
    <Screen title="Categories">
      <AppText weight="semibold" style={{ fontSize: 28 }}>
        Find your next step.
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
      ) : !result.data?.length ? (
        <DataState
          message="No categories available."
          onAction={() => {
            void result.refetch();
          }}
        />
      ) : (
        result.data.map((category) => <CategoryRow key={category.slug} item={category} />)
      )}
    </Screen>
  );
}
