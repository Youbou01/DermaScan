import { useEffect, useState } from 'react';
import { FlatList, View, Image, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { Button, Input } from 'heroui-native';
import {
  Search,
  ScanLine,
  ArrowUpRight,
  X,
  UserRound,
  SlidersHorizontal,
} from 'lucide-react-native';
import { router, useLocalSearchParams } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useCategories, useProducts, useShelf } from '@/lib/api/queries';
import type { Filters, RiskBand } from '@/lib/api/types';
import { colors } from '@/lib/theme';
import { AppText } from '@/components/AppText';
import { ProductCard } from '@/components/ProductCard';
import { DataState, LoadingState } from '@/components/DataState';
const setCategory = (value: string) => router.setParams({ category: value });
export default function Home() {
  const params = useLocalSearchParams<{ category?: string }>();
  const [query, setQuery] = useState('');
  const [debounced, setDebounced] = useState('');
  const category = params.category ?? '';
  const [section, setSection] = useState('top_rated');
  const [showFilters, setShowFilters] = useState(false);
  const [band, setBand] = useState<RiskBand | undefined>();
  const [include, setInclude] = useState('');
  const [exclude, setExclude] = useState('');
  const [applied, setApplied] = useState<Pick<Filters, 'include' | 'exclude'>>({});
  const insets = useSafeAreaInsets();
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 350);
    return () => clearTimeout(timer);
  }, [query]);
  const categories = useCategories();
  const filtering = !!(
    debounced ||
    category ||
    band ||
    applied.include?.length ||
    applied.exclude?.length
  );
  const search = useProducts(
    { q: debounced || undefined, category: category || undefined, band, ...applied },
    filtering,
  );
  const shelf = useShelf(section);
  const result = filtering ? search : shelf;
  const data = result.data?.pages.flatMap((page) => page.items) ?? [];
  const clear = () => {
    setQuery('');
    setDebounced('');
    setCategory('');
    setBand(undefined);
    setInclude('');
    setExclude('');
    setApplied({});
    void Haptics.selectionAsync();
  };
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ flex: 1, backgroundColor: colors.background }}
    >
      <FlatList
        data={data}
        keyExtractor={(item) => item.id}
        numColumns={2}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
        showsVerticalScrollIndicator={false}
        columnWrapperStyle={{ gap: 15 }}
        contentContainerStyle={{
          paddingHorizontal: 22,
          paddingTop: insets.top + 18,
          paddingBottom: insets.bottom + 28,
        }}
        ItemSeparatorComponent={() => <View style={{ height: 25 }} />}
        renderItem={({ item }) => <ProductCard product={item} />}
        refreshing={result.isRefetching && !result.isFetchingNextPage}
        onRefresh={() => {
          void result.refetch();
        }}
        onEndReached={() => {
          if (result.hasNextPage && !result.isFetchingNextPage && !result.isError)
            void result.fetchNextPage();
        }}
        onEndReachedThreshold={0.4}
        ListHeaderComponent={
          <>
            <View
              style={{
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 26,
              }}
            >
              <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center', flex: 1 }}>
                <ScanLine size={24} color={colors.ink} strokeWidth={1.8} />
                <AppText weight="bold" style={{ fontSize: 22, letterSpacing: -0.9 }}>
                  DermaScan
                </AppText>
              </View>
              <Button
                isIconOnly
                variant="tertiary"
                accessibilityLabel="Account"
                onPress={() => router.push('/account')}
              >
                <UserRound size={22} color={colors.ink} strokeWidth={1.8} />
              </Button>
            </View>
            <AppText
              weight="semibold"
              style={{ fontSize: 29, lineHeight: 36, letterSpacing: -1.2, marginBottom: 20 }}
            >
              Know your skincare.
            </AppText>
            <View style={{ flexDirection: 'row', gap: 10, alignItems: 'center', marginBottom: 22 }}>
              <View
                style={{
                  flex: 1,
                  flexDirection: 'row',
                  alignItems: 'center',
                  backgroundColor: colors.white,
                  borderRadius: 15,
                  borderWidth: 1,
                  borderColor: colors.border,
                  paddingLeft: 13,
                }}
              >
                <Search size={19} color={colors.muted} strokeWidth={1.8} />
                <Input
                  value={query}
                  onChangeText={setQuery}
                  maxLength={100}
                  placeholder="Product or brand"
                  accessibilityLabel="Search products"
                  autoCapitalize="none"
                  autoCorrect={false}
                  returnKeyType="search"
                  className="flex-1 border-0 bg-transparent"
                  style={{ fontSize: 12, height: 51, paddingHorizontal: 10 }}
                />
                {!!query && (
                  <Button
                    isIconOnly
                    size="sm"
                    variant="tertiary"
                    accessibilityLabel="Clear search"
                    onPress={() => setQuery('')}
                  >
                    <X size={16} color={colors.muted} strokeWidth={1.8} />
                  </Button>
                )}
              </View>
              <Button
                isIconOnly
                accessibilityLabel="Scan a product barcode"
                onPress={() => router.push('/scan')}
                style={{ height: 53, width: 53, borderRadius: 15 }}
              >
                <ScanLine size={24} color={colors.white} strokeWidth={1.8} />
              </Button>
            </View>
            {!filtering && (
              <View
                style={{
                  height: 209,
                  backgroundColor: colors.peach,
                  borderRadius: 20,
                  overflow: 'hidden',
                  marginBottom: 22,
                }}
              >
                <Image
                  source={require('@/assets/images/beauty-counter.png')}
                  resizeMode="cover"
                  style={{ position: 'absolute', width: '100%', height: 209, resizeMode: 'cover' }}
                />
                <View
                  style={{
                    padding: 18,
                    width: '64%',
                    height: '100%',
                    justifyContent: 'space-between',
                  }}
                >
                  <AppText
                    weight="semibold"
                    style={{ fontSize: 23, lineHeight: 29, letterSpacing: -0.9 }}
                  >
                    Less guessing.{'\n'}More knowing.
                  </AppText>
                  <Button
                    size="sm"
                    variant="tertiary"
                    onPress={() => router.push('/analysis')}
                    style={{
                      alignSelf: 'flex-start',
                      paddingHorizontal: 0,
                      backgroundColor: 'transparent',
                    }}
                  >
                    <Button.Label style={{ fontSize: 12 }}>Read a label</Button.Label>
                    <ArrowUpRight size={16} color={colors.ink} strokeWidth={1.8} />
                  </Button>
                </View>
              </View>
            )}
            <View style={{ flexDirection: 'row', gap: 8, marginBottom: 18 }}>
              <Button
                size="sm"
                variant="secondary"
                onPress={() => router.push('/routines')}
                style={{ flex: 1 }}
              >
                <Button.Label numberOfLines={1}>Your routines</Button.Label>
              </Button>
              <Button
                size="sm"
                variant="tertiary"
                onPress={() => router.push('/profile')}
                style={{ flex: 1 }}
              >
                <Button.Label numberOfLines={1}>Skin profile</Button.Label>
              </Button>
            </View>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              style={{ marginHorizontal: -22, marginBottom: 18 }}
              contentContainerStyle={{ paddingHorizontal: 22, gap: 8 }}
            >
              {[{ slug: '', name: 'All' }, ...(categories.data ?? [])].map((item) => (
                <Button
                  key={item.slug}
                  size="sm"
                  variant={item.slug === category ? 'primary' : 'tertiary'}
                  onPress={() => {
                    setCategory(item.slug);
                    void Haptics.selectionAsync();
                  }}
                  style={{
                    borderRadius: 30,
                    borderWidth: item.slug === category ? 0 : 1,
                    borderColor: colors.border,
                    paddingHorizontal: 16,
                    backgroundColor: item.slug === category ? colors.ink : colors.white,
                  }}
                >
                  <Button.Label numberOfLines={1} style={{ fontSize: 12 }}>
                    {item.name}
                  </Button.Label>
                </Button>
              ))}
              <Button size="sm" variant="tertiary" onPress={() => router.push('/categories')}>
                <Button.Label>More categories</Button.Label>
              </Button>
            </ScrollView>
            {categories.isError && (
              <DataState
                error={categories.error}
                onAction={() => {
                  void categories.refetch();
                }}
              />
            )}
            <View
              style={{
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 8,
                marginBottom: 17,
              }}
            >
              <AppText weight="semibold" style={{ flex: 1, fontSize: 22, letterSpacing: -0.6 }}>
                {filtering
                  ? 'Search results'
                  : section === 'top_rated'
                    ? 'Top rated'
                    : 'Recently added'}
              </AppText>
              <Button
                isIconOnly
                size="sm"
                variant="tertiary"
                accessibilityLabel="Filters"
                onPress={() => {
                  setShowFilters(!showFilters);
                  void Haptics.selectionAsync();
                }}
              >
                <SlidersHorizontal size={20} color={colors.ink} strokeWidth={1.8} />
              </Button>
            </View>
            {!filtering && (
              <View style={{ flexDirection: 'row', gap: 8, marginBottom: 18 }}>
                {['top_rated', 'recently_added'].map((id) => (
                  <Button
                    key={id}
                    size="sm"
                    variant={section === id ? 'secondary' : 'tertiary'}
                    onPress={() => {
                      setSection(id);
                      void Haptics.selectionAsync();
                    }}
                  >
                    <Button.Label>{id === 'top_rated' ? 'Top rated' : 'New arrivals'}</Button.Label>
                  </Button>
                ))}
              </View>
            )}
            {showFilters && (
              <View style={{ gap: 12, marginBottom: 24 }}>
                <AppText weight="medium">Score band</AppText>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                  {(['low', 'moderate', 'high'] as const).map((value) => (
                    <Button
                      size="sm"
                      variant={band === value ? 'primary' : 'secondary'}
                      key={value}
                      onPress={() => {
                        setBand(band === value ? undefined : value);
                        void Haptics.selectionAsync();
                      }}
                    >
                      <Button.Label>
                        {value === 'low'
                          ? 'Low concern'
                          : value === 'moderate'
                            ? 'Moderate'
                            : 'High concern'}
                      </Button.Label>
                    </Button>
                  ))}
                </View>
                <Input
                  accessibilityLabel="Include ingredients"
                  placeholder="Include ingredients, separated by commas"
                  value={include}
                  onChangeText={setInclude}
                />
                <Input
                  accessibilityLabel="Exclude ingredients"
                  placeholder="Exclude ingredients, separated by commas"
                  value={exclude}
                  onChangeText={setExclude}
                />
                <Button
                  size="sm"
                  variant="secondary"
                  onPress={() => {
                    setApplied({
                      include: include
                        .split(',')
                        .map((v) => v.trim())
                        .filter(Boolean)
                        .slice(0, 10),
                      exclude: exclude
                        .split(',')
                        .map((v) => v.trim())
                        .filter(Boolean)
                        .slice(0, 10),
                    });
                    void Haptics.selectionAsync();
                  }}
                >
                  <Button.Label>Apply ingredients</Button.Label>
                </Button>
                <Button size="sm" variant="tertiary" onPress={clear}>
                  <Button.Label>Clear filters</Button.Label>
                </Button>
                <AppText style={{ fontSize: 11, color: colors.muted }}>
                  Category and ingredient filters show scored products only.
                </AppText>
              </View>
            )}
          </>
        }
        ListEmptyComponent={
          result.isPending ? (
            <LoadingState />
          ) : result.isError ? (
            <DataState
              error={result.error}
              onAction={() => {
                void result.refetch();
              }}
            />
          ) : (
            <DataState
              message="No products found."
              action={filtering ? 'Clear filters' : 'Refresh'}
              onAction={
                filtering
                  ? clear
                  : () => {
                      void result.refetch();
                    }
              }
            />
          )
        }
        ListFooterComponent={
          <View style={{ marginTop: 26, gap: 18 }}>
            {result.isFetchingNextPage && <LoadingState />}
            {data.length > 0 && result.isError && (
              <DataState
                error={result.error}
                onAction={() => {
                  if (result.hasNextPage) void result.fetchNextPage();
                  else void result.refetch();
                }}
              />
            )}
            <AppText style={{ fontSize: 11, color: colors.muted, lineHeight: 17 }}>
              Scores may be estimated. Open a product for details. Not medical advice.
            </AppText>
          </View>
        }
      />
    </KeyboardAvoidingView>
  );
}
